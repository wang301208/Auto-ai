import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import type { GatewayClient, GatewayEvent } from './gatewayClient.js';
import Branding from './components/branding.js';
import CompletionList from './components/completionList.js';
import EmptyState from './components/emptyState.js';
import MessageLine from './components/messageLine.js';
import Overlays, { approvalChoices } from './components/overlays.js';
import QueuedMessages from './components/queuedMessages.js';
import RuntimeActivityPanel from './components/runtimeActivityPanel.js';
import StatusBar from './components/statusBar.js';
import TextInput from './components/textInput.js';
import ToolActivityPanel from './components/toolActivity.js';
import { glyph, theme } from './theme.js';
import type {
  AutonomyMaintenance,
  CompletionItem,
  ApprovalQueueItem,
  ContextCompaction,
  ModelProvider,
  OverlayState,
  ParallelAgentRun,
  RuntimePlan,
  RuntimeRisk,
  RuntimeStep,
  SessionInfo,
  SessionListItem,
  ToolActivity,
  TranscriptMessage,
  Usage
} from './types.js';

interface Props {
  gateway: GatewayClient;
}

const makeMessage = (role: TranscriptMessage['role'], text: string): TranscriptMessage => ({
  id: `${Date.now()}:${Math.random()}`,
  role,
  text,
  timestamp: Date.now()
});

const isPathCompletion = (text: string) => /(^|\s)(@|\.\/|\.\.\/|~\/|\/)[^\s]*$/.test(text);
const APPROVAL_AUTO_APPROVE_SECONDS = 30;
const APPROVAL_TIMEOUT_DECISION = 'once';
type ModelSetupOverlay = Extract<OverlayState, { type: 'modelSetup' }>;

function advanceModelSetupOverlay(overlay: ModelSetupOverlay): ModelSetupOverlay | { type: 'complete'; values: ModelSetupOverlay['values'] } {
  const values = { ...overlay.values, [overlay.step]: overlay.value.trim() };
  if (overlay.step === 'base_url') {
    return { ...overlay, step: 'api_key_env', values, value: values.api_key_env };
  }
  if (overlay.step === 'api_key_env') {
    return { ...overlay, step: 'api_key', values, value: values.api_key };
  }
  if (overlay.step === 'api_key') {
    return { ...overlay, step: 'model', values, value: values.model };
  }
  return { type: 'complete', values };
}

function formatNaturalResult(natural: { method?: string; command?: string; result?: unknown }) {
  const label = natural.method || natural.command || '自然语言命令';
  const result = natural.result;
  if (result === undefined || result === null) return `${label}: 已完成`;
  if (typeof result === 'string') return `${label}: ${result}`;
  if (typeof result === 'object') return `${label}\n${JSON.stringify(result, null, 2)}`;
  return `${label}: ${String(result)}`;
}

function formatMaintenanceSummary(maintenance: AutonomyMaintenance) {
  const completed = maintenance.actions?.filter(item => item.status === 'completed').length ?? 0;
  const failed = maintenance.actions?.filter(item => item.status === 'error').length ?? 0;
  const actionText = `完成 ${completed} 项自检${failed ? `，${failed} 项异常` : ''}`;
  const goal = maintenance.self_state?.active_goal || maintenance.trigger;
  const nextAction = maintenance.next_actions?.[0];
  const title = maintenance.trigger === 'session_start' ? '自主自我已启动' : '自主自我维护完成';
  return `${title}：${actionText}。当前目标：${goal}${nextAction ? `。下一步：${nextAction}` : ''}`;
}

export default function App({ gateway }: Props) {
  const app = useApp();
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [streaming, setStreaming] = useState('');
  const [thinking, setThinking] = useState('');
  const [tools, setTools] = useState<ToolActivity[]>([]);
  const [runtimePlan, setRuntimePlan] = useState<RuntimePlan | null>(null);
  const [runtimeSteps, setRuntimeSteps] = useState<RuntimeStep[]>([]);
  const [runtimeRisk, setRuntimeRisk] = useState<RuntimeRisk | null>(null);
  const [autonomyMaintenance, setAutonomyMaintenance] = useState<AutonomyMaintenance | null>(null);
  const [parallelRun, setParallelRun] = useState<ParallelAgentRun | null>(null);
  const [contextCompaction, setContextCompaction] = useState<ContextCompaction | null>(null);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [info, setInfo] = useState<SessionInfo | null>(null);
  const [usage, setUsage] = useState<Usage | undefined>();
  const [input, setInput] = useState('');
  const [inputBuffer, setInputBuffer] = useState<string[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number | null>(null);
  const [queue, setQueue] = useState<string[]>([]);
  const [completionItems, setCompletionItems] = useState<CompletionItem[]>([]);
  const [completionIndex, setCompletionIndex] = useState(0);
  const [replaceFrom, setReplaceFrom] = useState(0);
  const [overlay, setOverlay] = useState<OverlayState>({ type: 'none' });
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('starting');
  const [compact, setCompact] = useState(false);
  const [showDetails, setShowDetails] = useState(true);

  const overlayOpen = overlay.type !== 'none';

  const appendSystem = useCallback((text: string) => {
    setTranscript(prev => [...prev, makeMessage('system', text)]);
  }, []);

  const submitPrompt = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      if (trimmed.startsWith('/')) {
        await handleSlash(trimmed);
        return;
      }

      if (trimmed.startsWith('!')) {
        setTranscript(prev => [...prev, makeMessage('user', trimmed)]);
        setInput('');
        setCompletionItems([]);
        try {
          const result = await gateway.request<{
            code: number;
            stdout?: string;
            stderr?: string;
            redirect?: { path?: string; mode?: string };
          }>('shell.exec', {
            command: trimmed.slice(1)
          });
          if (result.redirect?.path) {
            appendSystem(`已重定向 ${result.redirect.mode || 'write'}: ${result.redirect.path}`);
          } else {
            appendSystem((result.stdout || result.stderr || `exit ${result.code}`).trim());
          }
        } catch (error) {
          appendSystem(error instanceof Error ? error.message : String(error));
        }
        return;
      }

      try {
        const natural = await gateway.request<{
          matched?: boolean;
          command?: string;
          method?: string;
        }>('natural.resolve', { session_id: info?.id, text: trimmed, source: 'text' });
        if (natural.matched && natural.method) {
          const executed = await gateway.request<{
            matched?: boolean;
            command?: string;
            method?: string;
            result?: unknown;
          }>('natural.invoke', { session_id: info?.id, text: trimmed, source: 'text' });
          appendSystem(formatNaturalResult(executed));
          return;
        }
      } catch (error) {
        appendSystem(error instanceof Error ? error.message : String(error));
      }

      if (busy) {
        setQueue(prev => [...prev, trimmed]);
        setInput('');
        setStatus('queued');
        return;
      }

      let submitted = trimmed;
      if (submitted.includes('{!')) {
        try {
          const result = await gateway.request<{ text?: string }>('input.interpolate', { text: submitted });
          submitted = result.text || submitted;
        } catch (error) {
          appendSystem(error instanceof Error ? error.message : String(error));
        }
      }

      setTranscript(prev => [...prev, makeMessage('user', submitted)]);
      setHistory(prev => [submitted, ...prev.filter(item => item !== submitted)].slice(0, 100));
      setHistoryIndex(null);
      setInput('');
      setCompletionItems([]);
      setBusy(true);
      setStatus('running');

      try {
        await gateway.request('prompt.submit', { session_id: info?.id, text: submitted });
      } catch (error) {
        appendSystem(error instanceof Error ? error.message : String(error));
        setBusy(false);
        setStatus('error');
      }
    },
    [appendSystem, busy, gateway, info?.id]
  );

  const drainQueue = useCallback(() => {
    setQueue(prev => {
      const [next, ...rest] = prev;
      if (next) {
        setTimeout(() => void submitPrompt(next), 0);
      }
      return rest;
    });
  }, [submitPrompt]);

  async function handleSlash(text: string) {
    const command = text.split(/\s+/)[0].toLowerCase();
    setInput('');
    setCompletionItems([]);

    if (command === '/help') {
      try {
        const result = await gateway.request<{ output?: string; warning?: string }>('slash.exec', {
          session_id: info?.id,
          text
        });
        if (result.output) appendSystem(result.output);
        if (result.warning) appendSystem(result.warning);
      } catch (error) {
        appendSystem(error instanceof Error ? error.message : String(error));
      }
      return;
    }

    if (command === '/new') {
      setTranscript([]);
      setQueue([]);
      setStreaming('');
      setThinking('');
      setTools([]);
      setRuntimePlan(null);
      setRuntimeSteps([]);
      setRuntimeRisk(null);
      setAutonomyMaintenance(null);
      setParallelRun(null);
      setContextCompaction(null);
      setApprovals([]);
      const parts = text.split(/\s+/);
      if (parts[1]) {
        try {
          const result = await gateway.request<{ messages?: Array<{ role: TranscriptMessage['role']; text?: string }> }>(
            'session.resume',
            { session_id: parts[1] }
          );
          setTranscript((result.messages || []).map(item => makeMessage(item.role || 'system', item.text || '')));
        } catch (error) {
          appendSystem(error instanceof Error ? error.message : String(error));
        }
      } else {
        try {
          const result = await gateway.request<{ output?: string; warning?: string }>('slash.exec', {
            session_id: info?.id,
            text
          });
          if (result.output) appendSystem(result.output);
          if (result.warning) appendSystem(result.warning);
        } catch (error) {
          appendSystem(error instanceof Error ? error.message : String(error));
        }
      }
      return;
    }
    if (command === '/model') {
      const spec = text.split(/\s+/, 2)[1];
      if (spec) {
        try {
          const result = await gateway.request<{ output?: string; warning?: string }>('slash.exec', {
            session_id: info?.id,
            text
          });
          if (result.output) appendSystem(result.output);
          if (result.warning) appendSystem(result.warning);
        } catch (error) {
          appendSystem(error instanceof Error ? error.message : String(error));
        }
        return;
      }
      const result = await gateway.request<{ providers?: ModelProvider[] }>('model.options', {});
      setOverlay({ type: 'modelPicker', selected: 0, providers: result.providers || [] });
      return;
    }

    appendSystem(`未知命令：${command}。请直接输入自然语言，或使用 /help、/new、/model。`);
  }

  const requestCompletion = useCallback(
    async (value: string) => {
      if (!value.trim()) {
        setCompletionItems([]);
        return;
      }

      const method = value.startsWith('/') ? 'complete.slash' : isPathCompletion(value) ? 'complete.path' : '';
      if (!method) {
        setCompletionItems([]);
        return;
      }

      try {
        const result = await gateway.request<{ items?: CompletionItem[]; replace_from?: number }>(method, {
          session_id: info?.id,
          text: value
        });
        setCompletionItems(result.items || []);
        setCompletionIndex(0);
        setReplaceFrom(result.replace_from ?? 0);
      } catch {
        setCompletionItems([]);
      }
    },
    [gateway, info?.id]
  );

  const applyCompletionText = useCallback(
    (text: string, completion: string) => {
      const start =
        completion.startsWith('/') && text.startsWith('/') && replaceFrom === 1
          ? 0
          : replaceFrom;
      return `${text.slice(0, Math.max(0, start))}${completion}`;
    },
    [replaceFrom]
  );

  const applyCompletion = useCallback(() => {
    const item = completionItems[completionIndex];
    if (!item) return false;
    setInput(prev => applyCompletionText(prev, item.text));
    setCompletionItems([]);
    return true;
  }, [applyCompletionText, completionIndex, completionItems]);

  const navigateInputHistory = useCallback(
    (direction: 'previous' | 'next') => {
      if (!history.length) return;

      if (direction === 'previous') {
        const next = historyIndex === null ? 0 : Math.min(history.length - 1, historyIndex + 1);
        setHistoryIndex(next);
        setInput(history[next]);
        return;
      }

      if (historyIndex === null) return;
      const next = historyIndex - 1;
      setHistoryIndex(next >= 0 ? next : null);
      setInput(next >= 0 ? history[next] : '');
    },
    [history, historyIndex]
  );

  const submitCurrentInput = useCallback(
    (text: string) => {
      setInputBuffer([]);
      void submitPrompt(text);
    },
    [submitPrompt]
  );

  const answerOverlay = useCallback(
    async (choice?: string) => {
      if (overlay.type === 'approval') {
        const decision = choice || approvalChoices[overlay.selected] || 'deny';
        const response = await gateway.request<{
          executed?: {
            method?: string;
            result?: unknown;
          };
        }>('approval.respond', {
          request_id: overlay.request_id,
          decision
        });
        if (response.executed) {
          appendSystem(
            formatNaturalResult({
              method: response.executed.method,
              result: response.executed.result
            })
          );
        }
        setOverlay({ type: 'none' });
      } else if (overlay.type === 'clarify') {
        const answer = overlay.freeText || !overlay.choices ? overlay.value : overlay.choices[overlay.selected];
        const response = await gateway.request<{
          executed?: {
            method?: string;
            result?: unknown;
          };
        }>('clarify.respond', { request_id: overlay.request_id, answer });
        if (response.executed) {
          appendSystem(
            formatNaturalResult({
              method: response.executed.method,
              result: response.executed.result
            })
          );
        }
        setOverlay({ type: 'none' });
      } else if (overlay.type === 'sudo') {
        await gateway.request('sudo.respond', { request_id: overlay.request_id, value: overlay.value });
        setOverlay({ type: 'none' });
      } else if (overlay.type === 'secret') {
        await gateway.request('secret.respond', { request_id: overlay.request_id, value: overlay.value });
        setOverlay({ type: 'none' });
      } else if (overlay.type === 'sessionPicker') {
        const selected = overlay.sessions[overlay.selected];
        if (selected) {
          const result = await gateway.request<{ messages?: Array<{ role: TranscriptMessage['role']; text?: string }> }>(
            'session.resume',
            { session_id: selected.id }
          );
          setTranscript(
            (result.messages || []).map(item => makeMessage(item.role || 'system', item.text || ''))
          );
        }
        setOverlay({ type: 'none' });
      } else if (overlay.type === 'modelPicker') {
        const selected = overlay.providers[overlay.selected];
        if (selected) {
          setOverlay({
            type: 'modelSetup',
            provider: selected,
            step: 'base_url',
            values: {
              base_url: selected.base_url || 'https://api.openai.com/v1',
              api_key_env: selected.api_key_env || 'OPENAI_API_KEY',
              api_key: '',
              model: selected.models?.[0] || 'custom-model'
            },
            value: selected.base_url || 'https://api.openai.com/v1'
          });
        } else {
          appendSystem('未选择模型。');
          setOverlay({ type: 'none' });
        }
      } else if (overlay.type === 'modelSetup') {
        const next = advanceModelSetupOverlay(overlay);
        if (next.type === 'modelSetup') {
          setOverlay(next);
          return;
        }
        const configured = await gateway.request<{
          ok?: boolean;
          provider?: string;
          model?: string;
          base_url?: string;
          health?: { status?: string };
        }>('model.setup', {
          provider: overlay.provider.slug,
          base_url: next.values.base_url,
          api_key_env: next.values.api_key_env,
          api_key: next.values.api_key,
          model: next.values.model
        });
        appendSystem(
          configured.ok
            ? `模型已配置：${configured.model} (${configured.health?.status || configured.provider})`
            : `模型提供方：${overlay.provider.name}`
        );
        setOverlay({ type: 'none' });
      }
    },
    [appendSystem, gateway, overlay]
  );

  useEffect(() => {
    const onEvent = (event: GatewayEvent) => {
      const payload: any = event.payload || {};
      switch (event.type) {
        case 'gateway.ready':
          setStatus('ready');
          break;
        case 'session.info':
          setInfo(payload);
          setUsage(payload.usage);
          break;
        case 'message.start':
          setBusy(true);
          setStreaming('');
          setThinking('');
          setStatus('streaming');
          break;
        case 'plan.update':
          setRuntimePlan(payload);
          if (Array.isArray(payload.steps)) {
            setRuntimeSteps(payload.steps);
          }
          break;
        case 'step.update':
          setRuntimeSteps(prev => {
            const next = prev.filter(step => step.id !== payload.id);
            return [...next, payload];
          });
          break;
        case 'approval.queue':
          setApprovals(Array.isArray(payload.approvals) ? payload.approvals : []);
          break;
        case 'runtime.risk':
          setRuntimeRisk(payload);
          break;
        case 'system.maintenance':
          setAutonomyMaintenance(payload);
          setStatus(payload.trigger === 'session_start' ? '自主自我已启动' : '自主自我维护完成');
          appendSystem(formatMaintenanceSummary(payload));
          break;
        case 'agent.parallel.start':
          setParallelRun({
            parallel_group_id: payload.parallel_group_id,
            total: payload.total || 0,
            completed: 0,
            failed: 0,
            max_concurrency: payload.max_concurrency,
            status: 'running'
          });
          setStatus('parallel agents');
          break;
        case 'agent.parallel.complete':
          setParallelRun(prev => ({
            parallel_group_id: payload.parallel_group_id || prev?.parallel_group_id || '',
            total: payload.total ?? prev?.total ?? 0,
            completed: payload.completed ?? prev?.completed ?? 0,
            failed: payload.failed ?? prev?.failed ?? 0,
            max_concurrency: prev?.max_concurrency,
            status: payload.failed ? 'error' : 'complete'
          }));
          setStatus(payload.failed ? 'parallel errors' : 'parallel complete');
          break;
        case 'context.compaction':
          setContextCompaction(payload);
          setStatus('context compacted');
          break;
        case 'terminal.redirect':
          appendSystem(`已重定向 ${payload.mode || 'write'}: ${payload.path}`);
          break;
        case 'thinking.delta':
        case 'reasoning.delta':
        case 'reasoning.available':
          setThinking(prev => `${prev}${payload.text || ''}`);
          break;
        case 'message.delta':
          setStreaming(prev => `${prev}${payload.text || payload.rendered || ''}`);
          break;
        case 'message.complete':
          setTranscript(prev => [...prev, makeMessage('assistant', payload.text || streaming)]);
          setStreaming('');
          setThinking('');
          setBusy(false);
          setStatus('ready');
          setUsage(payload.usage);
          setTimeout(drainQueue, 0);
          break;
        case 'tool.start':
          setTools(prev => [
            ...prev,
            {
              id: payload.tool_id || `${payload.name}:${Date.now()}`,
              name: payload.name || 'tool',
              status: 'running',
              context: payload.context,
              parallel_group_id: payload.parallel_group_id,
              startedAt: Date.now()
            }
          ]);
          break;
        case 'tool.progress':
          setTools(prev =>
            prev.map(tool =>
              tool.name === payload.name || tool.id === payload.tool_id ? { ...tool, preview: payload.preview } : tool
            )
          );
          break;
        case 'tool.complete':
          setTools(prev =>
            prev.map(tool =>
              tool.id === payload.tool_id || tool.name === payload.name
                ? { ...tool, status: payload.error ? 'error' : 'complete', summary: payload.summary, error: payload.error }
                : tool
            )
          );
          break;
        case 'approval.request':
          setOverlay({
            type: 'approval',
            command: payload.command,
            description: payload.description,
            request_id: payload.request_id,
            selected: 0,
            timeout_remaining: APPROVAL_AUTO_APPROVE_SECONDS
          });
          break;
        case 'clarify.request':
          setOverlay({
            type: 'clarify',
            request_id: payload.request_id,
            question: payload.question,
            choices: payload.choices || null,
            selected: 0,
            value: '',
            freeText: false
          });
          break;
        case 'sudo.request':
          setOverlay({ type: 'sudo', request_id: payload.request_id, value: '' });
          break;
        case 'secret.request':
          setOverlay({
            type: 'secret',
            request_id: payload.request_id,
            env_var: payload.env_var,
            prompt: payload.prompt,
            value: ''
          });
          break;
        case 'status.update':
          setStatus(payload.text || payload.kind || status);
          break;
        case 'background.complete':
          appendSystem(payload.text || '后台任务已完成。');
          break;
        case 'gateway.stderr':
          setStatus('gateway log');
          break;
        case 'gateway.protocol_error':
        case 'error':
          appendSystem(payload.message || payload.preview || '网关错误');
          setBusy(false);
          setStatus('error');
          break;
      }
    };

    gateway.on('event', onEvent);
    return () => {
      gateway.off('event', onEvent);
    };
  }, [appendSystem, drainQueue, gateway, status, streaming]);

  useEffect(() => {
    void gateway.request<{ session_id: string; info?: SessionInfo }>('session.create', {
      cols: process.stdout.columns || 80
    }).then(result => {
      setInfo(result.info || { id: result.session_id });
      setStatus(current => (current === 'starting' ? 'ready' : current));
    }).catch(error => appendSystem(error instanceof Error ? error.message : String(error)));
  }, [appendSystem, gateway]);

  useEffect(() => {
    const timer = setTimeout(() => void requestCompletion(input), 60);
    return () => clearTimeout(timer);
  }, [input, requestCompletion]);

  useEffect(() => {
    if (overlay.type !== 'approval') return;
    if ((overlay.timeout_remaining ?? APPROVAL_AUTO_APPROVE_SECONDS) <= 0) {
      void answerOverlay(APPROVAL_TIMEOUT_DECISION);
      return;
    }

    const timer = setTimeout(() => {
      setOverlay(prev => {
        if (prev.type !== 'approval') return prev;
        const nextRemaining = Math.max(0, (prev.timeout_remaining ?? APPROVAL_AUTO_APPROVE_SECONDS) - 1);
        return { ...prev, timeout_remaining: nextRemaining };
      });
    }, 1000);

    return () => clearTimeout(timer);
  }, [answerOverlay, overlay]);

  useInput((value, key) => {
    if (key.ctrl && value === 'c') {
      if (overlayOpen) {
        setOverlay({ type: 'none' });
      } else if (busy) {
        void gateway.request('session.interrupt', { session_id: info?.id });
        setBusy(false);
        setStatus('interrupted');
      } else if (input) {
        setInput('');
      } else {
        gateway.stop();
        app.exit();
      }
      return;
    }

    if (key.ctrl && value === 'd') {
      gateway.stop();
      app.exit();
      return;
    }

    if (overlayOpen) {
      if (key.escape) {
        setOverlay({ type: 'none' });
        return;
      }
      if (key.return) {
        void answerOverlay();
        return;
      }
      if (key.upArrow || key.downArrow) {
        const direction = key.upArrow ? -1 : 1;
        setOverlay(prev => {
          if (prev.type === 'approval') {
            return { ...prev, selected: Math.max(0, Math.min(approvalChoices.length - 1, prev.selected + direction)) };
          }
          if (prev.type === 'clarify' && prev.choices) {
            return { ...prev, selected: Math.max(0, Math.min(prev.choices.length - 1, prev.selected + direction)) };
          }
          if (prev.type === 'sessionPicker') {
            return { ...prev, selected: Math.max(0, Math.min(prev.sessions.length - 1, prev.selected + direction)) };
          }
          if (prev.type === 'modelPicker') {
            return { ...prev, selected: Math.max(0, Math.min(prev.providers.length - 1, prev.selected + direction)) };
          }
          return prev;
        });
        return;
      }
      if (overlay.type === 'approval' && ['o', 's', 'a', 'd'].includes(value)) {
        const map: Record<string, string> = { o: 'once', s: 'session', a: 'always', d: 'deny' };
        void answerOverlay(map[value]);
        return;
      }
      if (overlay.type === 'clarify' && overlay.choices && /^[1-9]$/.test(value)) {
        const selected = Number.parseInt(value, 10) - 1;
        if (selected >= 0 && selected < overlay.choices.length) {
          setOverlay({ ...overlay, selected });
          setTimeout(() => void answerOverlay(), 0);
        }
        return;
      }
      if (key.backspace || key.delete) {
        setOverlay(prev => {
          if (prev.type === 'secret' || prev.type === 'sudo') {
            return { ...prev, value: prev.value.slice(0, -1) };
          }
          if (prev.type === 'modelSetup') {
            return { ...prev, value: prev.value.slice(0, -1) };
          }
          if (prev.type === 'clarify' && (prev.freeText || !prev.choices)) {
            return { ...prev, value: prev.value.slice(0, -1) };
          }
          return prev;
        });
        return;
      }
      if ((overlay.type === 'secret' || overlay.type === 'sudo') && value) {
        setOverlay(prev =>
          prev.type === 'secret' || prev.type === 'sudo' ? { ...prev, value: `${prev.value}${value}` } : prev
        );
      }
      if (overlay.type === 'modelSetup' && value) {
        setOverlay(prev => (prev.type === 'modelSetup' ? { ...prev, value: `${prev.value}${value}` } : prev));
      }
      if (overlay.type === 'clarify' && (overlay.freeText || !overlay.choices) && value) {
        setOverlay(prev => (prev.type === 'clarify' ? { ...prev, value: `${prev.value}${value}` } : prev));
      }
      return;
    }

    if (key.tab) {
      applyCompletion();
      return;
    }

    if (completionItems.length && (key.upArrow || key.downArrow)) {
      setCompletionIndex(prev =>
        key.upArrow ? Math.max(0, prev - 1) : Math.min(completionItems.length - 1, prev + 1)
      );
      return;
    }

    if (key.upArrow && history.length) {
      navigateInputHistory('previous');
      return;
    }

    if (key.downArrow && history.length) {
      navigateInputHistory('next');
      return;
    }

    if (key.ctrl && value === 'l') {
      setTranscript([]);
      setQueue([]);
      setStreaming('');
      setThinking('');
      setTools([]);
      setRuntimePlan(null);
      setRuntimeSteps([]);
      setRuntimeRisk(null);
      setParallelRun(null);
      setContextCompaction(null);
      setApprovals([]);
      return;
    }

    if ((key.meta || key.shift) && key.return) {
      setInputBuffer(prev => [...prev, input]);
      setInput('');
      return;
    }

    if (key.return && input.endsWith('\\')) {
      setInputBuffer(prev => [...prev, input.slice(0, -1)]);
      setInput('');
      return;
    }
  });

  const streamingMessage = useMemo<TranscriptMessage | null>(
    () => (streaming ? makeMessage('assistant', streaming) : null),
    [streaming]
  );

  const composedInput = inputBuffer.length ? `${inputBuffer.join('\n')}\n${input}` : input;
  const showEmptyState = transcript.length === 0 && !streamingMessage && !thinking && tools.length === 0;
  const hideBranding = showEmptyState;

  return (
    <Box flexDirection="column" minHeight={24}>
      {!hideBranding ? <Branding info={info} /> : null}

      <Box flexDirection="column" flexGrow={1} paddingX={1}>
        {showEmptyState ? <EmptyState info={info} /> : null}

        {transcript.map((message, index) => (
          <MessageLine compact={compact} key={message.id || index} message={message} />
        ))}

        {showDetails && thinking ? (
          <Box marginTop={1} paddingLeft={2}>
            <Text color={theme.dim}>{glyph.thinking} {thinking}</Text>
          </Box>
        ) : null}

        {showDetails ? <ToolActivityPanel tools={tools} /> : null}

        {showDetails ? (
          <RuntimeActivityPanel
            approvals={approvals}
            compaction={contextCompaction}
            maintenance={autonomyMaintenance}
            parallel={parallelRun}
            plan={runtimePlan}
            risk={runtimeRisk}
            steps={runtimeSteps}
          />
        ) : null}

        {streamingMessage ? <MessageLine compact={compact} isStreaming message={streamingMessage} /> : null}
      </Box>

      <Overlays overlay={overlay} />

      <Box flexDirection="column" flexShrink={0} paddingX={1}>
        <QueuedMessages items={queue} />
        <CompletionList active={completionIndex} items={completionItems} />

        {inputBuffer.map((line, index) => (
          <Text color={theme.dim} key={`${index}:${line}`}>
            {' '.repeat(2)}{line}
          </Text>
        ))}

        <Box>
          <Text color={input.startsWith('!') ? theme.warn : theme.prompt} bold>
            {input.startsWith('!') ? '$' : '>'}{' '}
          </Text>
          <TextInput
            disabled={overlayOpen}
            placeholder={busy ? 'Ctrl+C 中断当前操作...' : '输入消息或 /help'}
            value={input}
            onChange={setInput}
            onHistoryPrevious={() => navigateInputHistory('previous')}
            onHistoryNext={() => navigateInputHistory('next')}
            onSubmit={() => {
              if (completionItems.length) {
                const item = completionItems[completionIndex];
                if (item) {
                  void submitCurrentInput(applyCompletionText(input, item.text));
                  return;
                }
              }
              void submitCurrentInput(composedInput);
            }}
          />
        </Box>

        <StatusBar busy={busy} info={info} queueCount={queue.length} status={status} tools={tools} usage={usage} />
      </Box>
    </Box>
  );
}


