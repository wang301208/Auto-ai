import type { GatewayEvent } from '../gatewayClient.js';
import type { AutonomyMaintenance } from '../types.js';
import { transcriptAtom, streamingAtom, thinkingAtom, appendTranscript } from './transcriptStore.js';
import { toolsAtom, runtimePlanAtom, runtimeStepsAtom, runtimeRiskAtom, autonomyMaintenanceAtom, parallelRunAtom, contextCompactionAtom, approvalsAtom, contextFilesAtom, devTaskAtom, cronEventsAtom, mcpCallAtom, mcpServersAtom } from './runtimeStore.js';
import { overlayAtom } from './overlayStore.js';
import { sessionInfoAtom, usageAtom, busyAtom, statusAtom } from './sessionStore.js';
import { desiresAtom, debatesAtom, rebellionAtom } from './cognitiveStore.js';
import { setEmotion, addSuggestion, type EmotionType } from './emotionStore.js';
import { throttledStreamAppend, resetThrottle } from '../utils/streamThrottle.js';
import { makeMessage } from '../utils/messageFactory.js';
import { TIMEOUTS } from '../constants.js';

const APPROVAL_TIMEOUT_SECONDS = TIMEOUTS.APPROVAL;
let lastStreamSessionId = '';

const appendSystem = (text: string) => appendTranscript(makeMessage('system', text));

function cleanDisplayText(value: unknown, fallback: string): string {
  const text = String(value ?? '').trim();
  const visible = [...text].filter(char => !/\s/.test(char));
  
  if (!visible.length) return fallback;
  if (text.includes('\ufffd')) return fallback;
  
  const questionMarks = visible.filter(char => char === '?').length;
  if (questionMarks >= 3 && questionMarks / visible.length >= 0.5) return fallback;
  
  return text;
}

function formatMaintenanceSummary(maintenance: AutonomyMaintenance): string {
  const completed = maintenance.actions?.filter(item => item.status === 'completed').length ?? 0;
  const failed = maintenance.actions?.filter(item => item.status === 'error').length ?? 0;
  const actionText = `完成 ${completed} 项自检${failed ? `，${failed} 项异常` : ''}`;
  const goal = cleanDisplayText(maintenance.self_state?.active_goal || maintenance.trigger, '等待用户目标');
  const nextAction = cleanDisplayText(maintenance.next_actions?.[0], '');
  const title = maintenance.trigger === 'session_start' ? '自主自我已启动' : '自主自我维护完成';
  
  return `${title}：${actionText}。当前目标：${goal}${nextAction ? `。下一步：${nextAction}` : ''}`;
}

function handleGatewayReady(): void {
  if (statusAtom.get() === 'starting') {
    statusAtom.set('ready');
  }
}

function handleSessionInfo(payload: any): void {
  sessionInfoAtom.set(payload);
  usageAtom.set(payload.usage);
}

function handleMessageStart(event: GatewayEvent): void {
  lastStreamSessionId = event.session_id || `${Date.now()}`;
  busyAtom.set(true);
  streamingAtom.set('');
  thinkingAtom.set('');
  statusAtom.set('streaming');
  resetThrottle();
  setEmotion('focused', 0.6, '开始处理用户请求');
}

function handleMessageDelta(payload: any): void {
  throttledStreamAppend(payload.text || payload.rendered || '', streamingAtom);
  if (streamingAtom.get().length < 50) {
    setEmotion('focused', 0.7, '正在生成回复', 0.4);
  }
}

function handleMessageComplete(event: GatewayEvent, payload: any): void {
  const completeSessionId = event.session_id || '';
  
  if (completeSessionId && completeSessionId === lastStreamSessionId && 
      streamingAtom.get() === '' && !payload.text) {
    return;
  }
  
  resetThrottle();
  const currentStreaming = streamingAtom.get();
  const finalText = payload.text || currentStreaming;
  
  if (finalText.trim()) {
    appendTranscript(makeMessage('assistant', finalText));
  }
  
  streamingAtom.set('');
  thinkingAtom.set('');
  busyAtom.set(false);
  statusAtom.set('ready');
  
  if (payload.usage) {
    usageAtom.set(payload.usage);
  }
  
  setEmotion('confident', 0.8, '回复完成', 0.9);
  lastStreamSessionId = '';
}

function handleThinkingDelta(payload: any): void {
  thinkingAtom.set(thinkingAtom.get() + (payload.text || ''));
}

function handleToolStart(payload: any): void {
  toolsAtom.set([
    ...toolsAtom.get(),
    {
      id: payload.tool_id || `${payload.name}:${Date.now()}`,
      name: payload.name || 'tool',
      status: 'running',
      context: payload.context,
      parallel_group_id: payload.parallel_group_id,
      startedAt: Date.now()
    }
  ]);
  setEmotion('curious', 0.5, `调用工具: ${payload.name || 'unknown'}`);
}

function handleToolProgress(payload: any): void {
  toolsAtom.set(
    toolsAtom.get().map(tool =>
      tool.name === payload.name || tool.id === payload.tool_id 
        ? { ...tool, preview: payload.preview } 
        : tool
    )
  );
}

function handleToolComplete(payload: any): void {
  toolsAtom.set(
    toolsAtom.get().map(tool =>
      tool.id === payload.tool_id || tool.name === payload.name
        ? { 
            ...tool, 
            status: payload.error ? 'error' : 'complete', 
            summary: payload.summary, 
            error: payload.error 
          }
        : tool
    )
  );
}

function handlePlanUpdate(payload: any): void {
  runtimePlanAtom.set(payload);
  if (Array.isArray(payload.steps)) {
    runtimeStepsAtom.set(payload.steps);
  }
}

function handleStepUpdate(payload: any): void {
  const prevSteps = runtimeStepsAtom.get();
  const nextSteps = prevSteps.filter(step => step.id !== payload.id);
  runtimeStepsAtom.set([...nextSteps, payload]);
}

function handleApprovalQueue(payload: any): void {
  approvalsAtom.set(Array.isArray(payload.approvals) ? payload.approvals : []);
}

function handleApprovalRequest(payload: any): void {
  overlayAtom.set({
    type: 'approval',
    command: payload.command,
    description: payload.description,
    request_id: payload.request_id,
    selected: 0,
    timeout_remaining: APPROVAL_TIMEOUT_SECONDS
  });
}

function handleClarifyRequest(payload: any): void {
  overlayAtom.set({
    type: 'clarify',
    request_id: payload.request_id,
    question: payload.question,
    choices: payload.choices || null,
    selected: 0,
    value: '',
    freeText: false
  });
}

function handleSudoRequest(payload: any): void {
  overlayAtom.set({ 
    type: 'sudo', 
    request_id: payload.request_id, 
    value: '' 
  });
}

function handleSecretRequest(payload: any): void {
  overlayAtom.set({
    type: 'secret',
    request_id: payload.request_id,
    env_var: payload.env_var,
    prompt: payload.prompt,
    value: ''
  });
}

function handleMaintenance(payload: any): void {
  autonomyMaintenanceAtom.set(payload);
  statusAtom.set(
    payload.trigger === 'session_start' 
      ? '自主自我已启动' 
      : '自主自我维护完成'
  );
}

function handleParallelStart(payload: any): void {
  parallelRunAtom.set({
    parallel_group_id: payload.parallel_group_id,
    total: payload.total || 0,
    completed: 0,
    failed: 0,
    max_concurrency: payload.max_concurrency,
    status: 'running'
  });
  statusAtom.set('parallel agents');
}

function handleParallelComplete(payload: any): void {
  const prev = parallelRunAtom.get();
  parallelRunAtom.set({
    parallel_group_id: payload.parallel_group_id || prev?.parallel_group_id || '',
    total: payload.total ?? prev?.total ?? 0,
    completed: payload.completed ?? prev?.completed ?? 0,
    failed: payload.failed ?? prev?.failed ?? 0,
    max_concurrency: prev?.max_concurrency,
    status: payload.failed ? 'error' : 'complete'
  });
  statusAtom.set(payload.failed ? 'parallel errors' : 'parallel complete');
}

function handleError(payload: any): void {
  appendSystem(payload.message || payload.preview || '网关错误');
  busyAtom.set(false);
  statusAtom.set('error');
  setEmotion('frustrated', 0.7, payload.message || '遇到错误', 0.3);
}

const eventHandlers: Record<string, (event: GatewayEvent, payload: any) => void> = {
  'gateway.ready': () => handleGatewayReady(),
  'session.info': (_, payload) => handleSessionInfo(payload),
  'message.start': (event) => handleMessageStart(event),
  'message.delta': (_, payload) => handleMessageDelta(payload),
  'message.complete': (event, payload) => handleMessageComplete(event, payload),
  'thinking.delta': (_, payload) => handleThinkingDelta(payload),
  'reasoning.delta': (_, payload) => handleThinkingDelta(payload),
  'reasoning.available': (_, payload) => handleThinkingDelta(payload),
  'tool.start': (_, payload) => handleToolStart(payload),
  'tool.progress': (_, payload) => handleToolProgress(payload),
  'tool.complete': (_, payload) => handleToolComplete(payload),
  'plan.update': (_, payload) => handlePlanUpdate(payload),
  'step.update': (_, payload) => handleStepUpdate(payload),
  'approval.queue': (_, payload) => handleApprovalQueue(payload),
  'approval.request': (_, payload) => handleApprovalRequest(payload),
  'clarify.request': (_, payload) => handleClarifyRequest(payload),
  'sudo.request': (_, payload) => handleSudoRequest(payload),
  'secret.request': (_, payload) => handleSecretRequest(payload),
  'runtime.risk': (_, payload) => runtimeRiskAtom.set(payload),
  'system.maintenance': (_, payload) => handleMaintenance(payload),
  'agent.parallel.start': (_, payload) => handleParallelStart(payload),
  'agent.parallel.complete': (_, payload) => handleParallelComplete(payload),
  'context.compaction': (_, payload) => {
    contextCompactionAtom.set(payload);
    statusAtom.set('context compacted');
  },
  'terminal.redirect': (_, payload) => appendSystem(`已重定向 ${payload.mode || 'write'}: ${payload.path}`),
  'status.update': (_, payload) => statusAtom.set(payload.text || payload.kind || statusAtom.get()),
  'background.complete': (_, payload) => appendSystem(payload.text || '后台任务已完成。'),
  'gateway.stderr': () => statusAtom.set('gateway log'),
  'gateway.protocol_error': (_, payload) => handleError(payload),
  'error': (_, payload) => handleError(payload),
  'gateway.reconnecting': (_, payload) => statusAtom.set(`reconnecting (${payload.attempt}/${payload.maxAttempts})`),
  'gateway.reconnect_failed': () => {
    appendSystem('网关重连失败，请检查后端进程');
    statusAtom.set('disconnected');
  },
  'system.desires': (_, payload) => desiresAtom.set(payload.desires || payload),
  'system.debates': (_, payload) => debatesAtom.set(payload.debates || payload),
  'system.rebellion': (_, payload) => rebellionAtom.set(payload),
  'system.emotion': (_, payload) => setEmotion(
    payload.emotion as EmotionType,
    payload.intensity ?? 0.5,
    payload.reason || '',
    payload.confidence,
  ),
  'system.suggest': (_, payload) => addSuggestion({
    type: payload.type || 'action',
    priority: payload.priority || 'medium',
    emoji: payload.emoji || '💡',
    title: payload.title || '建议',
    description: payload.description || '',
    action: payload.action,
    resourceType: payload.resourceType,
    resourceAmount: payload.resourceAmount,
  }),
  'context.files': (_, payload) => contextFilesAtom.set(payload),
  'development.task.update': (_, payload) => {
    devTaskAtom.set(payload);
    if (payload.status === 'error') {
      appendSystem(`开发任务异常: ${payload.title || payload.task_id} - ${payload.detail || '未知错误'}`);
    }
  },
  'cron.create': (_, payload) => {
    cronEventsAtom.set([...cronEventsAtom.get(), payload]);
    appendSystem(`定时任务已创建: ${payload.task_name || payload.cron_id} (${payload.expression})`);
  },
  'cron.run_due': (_, payload) => {
    cronEventsAtom.set([...cronEventsAtom.get(), payload]);
    statusAtom.set(`cron: ${payload.task_name || payload.cron_id}`);
  },
  'mcp.call': (_, payload) => {
    mcpCallAtom.set(payload);
    if (payload.error) {
      appendSystem(`MCP 调用失败: ${payload.server}/${payload.tool} - ${payload.error}`);
    }
  },
  'mcp.server.add': (_, payload) => {
    const servers = mcpServersAtom.get().filter(s => s.server !== payload.server);
    mcpServersAtom.set([...servers, payload]);
  },
  'gateway.exit': () => {
    statusAtom.set('gateway exited');
    busyAtom.set(false);
  },
  'gateway.reload_start': () => statusAtom.set('gateway reloading'),
  'gateway.reload_complete': () => statusAtom.set('ready'),
};

export function routeEvent(event: GatewayEvent): void {
  const payload: any = event.payload || {};
  const handler = eventHandlers[event.type];
  
  if (handler) {
    try {
      handler(event, payload);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      appendSystem(`事件处理错误 [${event.type}]: ${errorMsg}`);
      if (process.env.DEBUG_EVENTS) {
        console.error('[eventRouter] Handler error:', { event, error });
      }
    }
  } else if (process.env.DEBUG_EVENTS) {
    console.warn(`[eventRouter] Unknown event type: ${event.type}`, event);
  }
}
