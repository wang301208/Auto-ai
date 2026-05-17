import { spawn, type ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

interface GatewayEvent<T = unknown> {
  type: string;
  session_id?: string;
  payload?: T;
}

interface PendingRequest {
  method: string;
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
  aborted?: boolean;
}

const REQUEST_TIMEOUT_MS = 30000;

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
  return (
    process.env['TUI_PYTHON_SRC_ROOT'] ||
    findProjectRoot(process.cwd()) ||
    path.resolve(import.meta.url?.replace(/^file:\/\//, 'file:///') || '', '..', '..')
  );
}

export class GatewayClient extends EventEmitter {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests = new Map<string, PendingRequest>();
  private logs: string[] = [];

  constructor() {
    super();
    this.setMaxListeners(0);
  }

  async start(): Promise<void> {
    if (this.process && !this.process.killed && this.process.exitCode === null) {
      return;
    }

    const python = process.env['TUI_PYTHON'] || process.env['PYTHON'] || 'python';
    const root = resolveProjectRoot();

    this.process = spawn(python, ['-m', 'tui_gateway.entry'], {
      cwd: root,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (!this.process.stdout || !this.process.stdin || !this.process.stderr) {
      throw new Error('Failed to spawn gateway process');
    }

    const stdout = readline.createInterface({ input: this.process.stdout, crlfDelay: Infinity });
    stdout.on('line', (line: string) => {
      try {
        this.handleMessage(JSON.parse(line));
      } catch {
        const preview = line.trim().slice(0, 240) || '(empty line)';
        this.pushLog(`[protocol] malformed stdout: ${preview}`);
        this.emitGatewayEvent({ type: 'gateway.protocol_error', payload: { preview } });
      }
    });

    const stderr = readline.createInterface({ input: this.process.stderr, crlfDelay: Infinity });
    stderr.on('line', (line: string) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      this.pushLog(trimmed);
      this.emitGatewayEvent({ type: 'gateway.stderr', payload: { line: trimmed } });
    });

    this.process.on('exit', code => {
      this.rejectPending(new Error(`gateway exited${code === null ? '' : ` (${code})`}`));
      this.emit('exit', code);
      this.emitGatewayEvent({ type: 'gateway.exit', payload: { code } });
    });

    this.process.on('error', error => {
      this.rejectPending(error);
      this.emitGatewayEvent({ type: 'gateway.stderr', payload: { line: `[spawn] ${error.message}` } });
    });
  }

  async request<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T> {
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
        resolve: resolve as (value: unknown) => void,
        reject,
        timeout,
        aborted: false,
      });

      this.process!.stdin!.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    });
  }

  getLogTail(limit = 20): string {
    return this.logs.slice(-Math.max(1, limit)).join('\n');
  }

  stop(): void {
    this.process?.kill();
    this.process = null;
  }

  private handleMessage(data: unknown): void {
    if (typeof data !== 'object' || data === null) return;

    const message = data as Record<string, unknown>;
    if ('id' in message) {
      const pending = this.pendingRequests.get(String(message['id']));
      if (!pending) return;
      clearTimeout(pending.timeout);
      this.pendingRequests.delete(String(message['id']));
      if ('error' in message) {
        pending.reject(new Error(String(message['error'])));
      } else {
        pending.resolve(message['result']);
      }
      return;
    }

    if (message['method'] === 'event' && (message['params'] as any)?.type) {
      this.emitGatewayEvent(message['params'] as GatewayEvent<unknown>);
      return;
    }

    if (typeof message['method'] === 'string') {
      this.emit(message['method'], message['params']);
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
}

export const gatewayClient = new GatewayClient();
