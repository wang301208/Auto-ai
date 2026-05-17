import { spawn, type ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';
import { fileURLToPath } from 'url';
import { RECONNECT_CONFIG, LOG_CONFIG, TIMEOUTS, DEFAULT_GATEWAY_CONFIG } from './constants.js';

export interface GatewayEvent<T = any> {
  type: string;
  session_id?: string;
  payload?: T;
}

interface PendingRequest {
  method: string;
  resolve: (value: any) => void;
  reject: (reason: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
  aborted?: boolean;
}

const REQUEST_TIMEOUT_MS = TIMEOUTS.RPC_REQUEST;

function findProjectRoot(start: string): string | null {
  let current = start;
  for (let index = 0; index < 8; index += 1) {
    if (fs.existsSync(path.join(current, 'tui_gateway', 'entry.py'))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function resolveProjectRoot(): string {
  const moduleDir = path.dirname(fileURLToPath(import.meta.url));
  return (
    process.env.TUI_PYTHON_SRC_ROOT ||
    findProjectRoot(process.cwd()) ||
    findProjectRoot(moduleDir) ||
    path.resolve(moduleDir, '..', '..')
  );
}

export class GatewayClient extends EventEmitter {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests = new Map<string, PendingRequest>();
  private logs: string[] = [];
  private restarting = false;
  private stopping = false;

  constructor() {
    super();
    this.setMaxListeners(0);
  }

  async start(): Promise<void> {
    if (this.process && !this.process.killed && this.process.exitCode === null) {
      return;
    }

    this.stopping = false;
    const python = process.env.TUI_PYTHON || process.env.PYTHON || 'python';
    const root = resolveProjectRoot();
    const cwd = process.env.TUI_CWD || root;
    const defaultConfigPath = path.join(root, 'config.yaml');
    const env = {
      ...process.env,
      LANG: process.env.LANG || 'zh_CN.UTF-8',
      LC_ALL: process.env.LC_ALL || 'zh_CN.UTF-8',
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1',
      LOCAL_AGENT_CONFIG_PATH: process.env.LOCAL_AGENT_CONFIG_PATH || defaultConfigPath,
      PYTHONPATH: process.env.PYTHONPATH ? `${root}${path.delimiter}${process.env.PYTHONPATH}` : root
    };

    this.process = spawn(python, ['-m', 'tui_gateway.entry'], {
      cwd,
      env,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (!this.process.stdout || !this.process.stdin || !this.process.stderr) {
      throw new Error('Failed to spawn gateway process');
    }

    const stdout = readline.createInterface({ input: this.process.stdout, crlfDelay: Infinity });
    stdout.on('line', line => {
      try {
        this.handleMessage(JSON.parse(line));
      } catch {
        const preview = line.trim().slice(0, 240) || '(empty line)';
        this.pushLog(`[protocol] malformed stdout: ${preview}`);
        this.emitGatewayEvent({ type: 'gateway.protocol_error', payload: { preview } });
      }
    });

    const stderr = readline.createInterface({ input: this.process.stderr, crlfDelay: Infinity });
    stderr.on('line', line => {
      const trimmed = line.trim();
      if (!trimmed) return;
      this.pushLog(trimmed);
      this.emitGatewayEvent({ type: 'gateway.stderr', payload: { line: trimmed } });
    });

    this.process.on('exit', code => {
      if (!this.restarting && !this.stopping) {
        this.rejectPending(new Error(`gateway exited${code === null ? '' : ` (${code})`}`));
      }
      this.emit('exit', code);
      this.emitGatewayEvent({ type: 'gateway.exit', payload: { code } });
    });

    this.process.on('error', error => {
      this.rejectPending(error);
      this.emitGatewayEvent({ type: 'gateway.stderr', payload: { line: `[spawn] ${error.message}` } });
    });
  }

  async request<T = any>(method: string, params: Record<string, any> = {}): Promise<T> {
    if (!this.process?.stdin || this.process.killed || this.process.exitCode !== null) {
      await this.start();
    }

    if (!this.process?.stdin) {
      return Promise.reject(new Error('gateway not running'));
    }

    const id = `r${++this.requestId}`;
    return new Promise<T>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`timeout: ${method}`));
      }, REQUEST_TIMEOUT_MS);

      this.pendingRequests.set(id, {
        method,
        resolve,
        reject,
        timeout,
        aborted: false,
      });

      this.process!.stdin!.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    });
  }

  /**
   * 创建可取消的请求
   */
  createCancellableRequest<T = any>(method: string, params: Record<string, any> = {}): {
    promise: Promise<T>;
    cancel: () => void;
  } {
    const id = `r${++this.requestId}`;
    let abortHandler: (() => void) | null = null;

    const promise = new Promise<T>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`timeout: ${method}`));
      }, REQUEST_TIMEOUT_MS);

      abortHandler = () => {
        clearTimeout(timeout);
        this.pendingRequests.delete(id);
        reject(new Error(`aborted: ${method}`));
      };

      this.pendingRequests.set(id, {
        method,
        resolve,
        reject,
        timeout,
        aborted: false,
      });

      if (!this.process?.stdin) {
        reject(new Error('gateway not running'));
        return;
      }

      this.process.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    });

    return {
      promise,
      cancel: () => {
        if (abortHandler) abortHandler();
      },
    };
  }

  /**
   * 带重试的请求
   */
  async requestWithRetry<T = any>(
    method: string,
    params: Record<string, any> = {},
    maxRetries: number = 3,
    baseDelayMs: number = 1000
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await this.request<T>(method, params);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        if (attempt < maxRetries - 1) {
          const delay = baseDelayMs * Math.pow(2, attempt);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError || new Error(`max retries exceeded: ${method}`);
  }

  async notify(method: string, params: Record<string, any> = {}): Promise<void> {
    if (!this.process?.stdin || this.process.killed || this.process.exitCode !== null) {
      await this.start();
    }
    this.process?.stdin?.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n');
  }

  getLogTail(limit = 20): string {
    return this.logs.slice(-Math.max(1, limit)).join('\n');
  }

  stop(): void {
    this.stopping = true;
    this.rejectPending(new Error('gateway stopped'));
    this.process?.kill();
    this.process = null;
  }

  private handleMessage(data: any): void {
    if ('id' in data) {
      const pending = this.pendingRequests.get(data.id);
      if (!pending) return;
      clearTimeout(pending.timeout);
      this.pendingRequests.delete(data.id);
      if (data.error) {
        pending.reject(new Error(data.error.message || `${pending.method} failed`));
      } else {
        pending.resolve(data.result);
      }
      return;
    }

    if (data.method === 'event' && data.params?.type) {
      this.emitGatewayEvent(data.params);
      if (data.params.type === 'gateway.reload_required') {
        void this.restartAfterReloadRequired(data.params.payload || {});
      }
      return;
    }

    if (typeof data.method === 'string') {
      this.emit(data.method, data.params);
    }
  }

  private emitGatewayEvent(event: GatewayEvent): void {
    this.emit('event', event);
    this.emit(event.type, event.payload);
  }

  private pushLog(line: string): void {
    this.logs.push(line.length > 4096 ? `${line.slice(0, 4096)}...` : line);
    if (this.logs.length > 200) {
      this.logs.splice(0, this.logs.length - 200);
    }
  }

  private rejectPending(error: Error): void {
    for (const pending of this.pendingRequests.values()) {
      clearTimeout(pending.timeout);
      pending.reject(error);
    }
    this.pendingRequests.clear();
  }

  private async restartAfterReloadRequired(payload: Record<string, any>): Promise<void> {
    if (this.restarting) return;
    this.restarting = true;
    this.pushLog(`[reload] restarting gateway: ${payload.reason || 'source changed'}`);
    this.emitGatewayEvent({ type: 'gateway.reload_start', payload });
    try {
      await this.restart();
      this.emitGatewayEvent({ type: 'gateway.reload_complete', payload });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.emitGatewayEvent({ type: 'gateway.stderr', payload: { line: `[reload] ${message}` } });
    } finally {
      this.restarting = false;
    }
  }

  private async restart(): Promise<void> {
    const oldProcess = this.process;
    if (oldProcess && !oldProcess.killed && oldProcess.exitCode === null) {
      oldProcess.kill();
      await new Promise<void>(resolve => {
        oldProcess.once('exit', () => resolve());
        setTimeout(resolve, 1500);
      });
    }
    this.process = null;
    await this.start();
  }
}


