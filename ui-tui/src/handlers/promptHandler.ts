import type { GatewayClient } from '../gatewayClient.js';
import type { ModelProvider, OverlayState, SessionInfo, TranscriptMessage } from '../types.js';
import { transcriptAtom, streamingAtom, thinkingAtom, appendTranscript, clearTranscript } from '../stores/transcriptStore.js';
import { toolsAtom, clearRuntime } from '../stores/runtimeStore.js';
import { overlayAtom, closeOverlay } from '../stores/overlayStore.js';
import { sessionInfoAtom, busyAtom, statusAtom } from '../stores/sessionStore.js';
import { inputAtom, inputBufferAtom, historyAtom, queueAtom, completionItemsAtom, completionIndexAtom, replaceFromAtom, scrollOffsetAtom, addToHistory } from '../stores/inputStore.js';
import { HISTORY_CONFIG, APPROVAL_CHOICES } from '../constants.js';
import { makeMessage } from '../utils/messageFactory.js';

const appendSystem = (text: string) => appendTranscript(makeMessage('system', text));

export function formatNaturalResult(natural: { method?: string; command?: string; result?: unknown }) {
  const label = natural.method || natural.command || '自然语言命令';
  
  if (natural.result === undefined || natural.result === null) {
    return `${label}: 已完成`;
  }
  
  if (typeof natural.result === 'string') {
    return `${label}: ${natural.result}`;
  }
  
  if (typeof natural.result === 'object') {
    return `${label}\n${JSON.stringify(natural.result, null, 2)}`;
  }
  
  return `${label}: ${String(natural.result)}`;
}

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

async function handleNaturalCommand(text: string, gateway: GatewayClient): Promise<void> {
  appendTranscript(makeMessage('user', text));
  inputAtom.set(''); 
  completionItemsAtom.set([]);
  
  try {
    const result = await gateway.request<{ 
      matched?: boolean; 
      command?: string; 
      method?: string; 
      result?: unknown 
    }>('natural.invoke', { 
      session_id: sessionInfoAtom.get()?.id, 
      text: `run command ${text.slice(1)}`, 
      source: 'text' 
    });
    
    appendSystem(formatNaturalResult(result));
  } catch (error) { 
    appendSystem(error instanceof Error ? error.message : String(error)); 
  }
}

async function tryNaturalResolve(text: string, gateway: GatewayClient): Promise<boolean> {
  try {
    const natural = await gateway.request<{ 
      matched?: boolean; 
      command?: string; 
      method?: string 
    }>('natural.resolve', { 
      session_id: sessionInfoAtom.get()?.id, 
      text, 
      source: 'text' 
    });
    
    if (natural.matched && natural.method) {
      const executed = await gateway.request<{ 
        matched?: boolean; 
        command?: string; 
        method?: string; 
        result?: unknown 
      }>('natural.invoke', { 
        session_id: sessionInfoAtom.get()?.id, 
        text, 
        source: 'text' 
      });
      
      appendSystem(formatNaturalResult(executed));
      return true;
    }
  } catch (error) { 
    appendSystem(error instanceof Error ? error.message : String(error));
  }
  
  return false;
}

async function interpolateText(text: string, gateway: GatewayClient): Promise<string> {
  if (!text.includes('{!')) return text;
  
  try { 
    const result = await gateway.request<{ text?: string }>('input.interpolate', { text });
    return result.text || text;
  } catch (error) { 
    appendSystem(error instanceof Error ? error.message : String(error));
    return text;
  }
}

async function handleSlashHelp(text: string, gateway: GatewayClient): Promise<void> {
  try { 
    const result = await gateway.request<{ 
      output?: string; 
      warning?: string 
    }>('slash.exec', { 
      session_id: sessionInfoAtom.get()?.id, 
      text 
    });
    
    if (result.output) appendSystem(result.output); 
    if (result.warning) appendSystem(result.warning); 
  } catch (error) { 
    appendSystem(error instanceof Error ? error.message : String(error));
  }
}

async function handleSlashNew(text: string, gateway: GatewayClient): Promise<void> {
  clearTranscript(); 
  scrollOffsetAtom.set(0); 
  queueAtom.set([]); 
  clearRuntime();
  
  const parts = text.split(/\s+/);
  
  if (parts[1]) { 
    try { 
      const result = await gateway.request<{ 
        messages?: Array<{ 
          role: TranscriptMessage['role']; 
          text?: string 
        }> 
      }>('session.resume', { 
        session_id: parts[1] 
      });
      
      transcriptAtom.set(
        (result.messages || []).map(item => 
          makeMessage(item.role || 'system', item.text || '')
        )
      );
      
      scrollOffsetAtom.set(0); 
    } catch (error) { 
      appendSystem(error instanceof Error ? error.message : String(error));
    } 
  } else { 
    await handleSlashHelp(text, gateway);
  }
}

async function handleSlashModel(text: string, gateway: GatewayClient): Promise<void> {
  const spec = text.split(/\s+/, 2)[1];
  
  if (spec) { 
    await handleSlashHelp(text, gateway);
    return;
  }
  
  const result = await gateway.request<{ 
    providers?: ModelProvider[] 
  }>('model.options', {});
  
  overlayAtom.set({ 
    type: 'modelPicker', 
    selected: 0, 
    providers: result.providers || [] 
  });
}

async function handleSlash(text: string, gateway: GatewayClient): Promise<void> {
  const command = text.split(/\s+/)[0].toLowerCase();
  inputAtom.set(''); 
  completionItemsAtom.set([]);
  
  switch (command) {
    case '/help':
      await handleSlashHelp(text, gateway);
      break;
    case '/new':
      await handleSlashNew(text, gateway);
      break;
    case '/model':
      await handleSlashModel(text, gateway);
      break;
    default:
      appendSystem(`未知命令：${command}。请直接输入自然语言，或使用 /help、/new、/model。`);
  }
}

export async function submitPrompt(text: string, gateway: GatewayClient) {
  const trimmed = text.trim();
  
  if (!trimmed) return;
  
  if (trimmed.startsWith('/')) { 
    await handleSlash(trimmed, gateway); 
    return; 
  }
  
  if (trimmed.startsWith('!')) {
    await handleNaturalCommand(trimmed, gateway);
    return;
  }
  
  const naturalHandled = await tryNaturalResolve(trimmed, gateway);
  if (naturalHandled) return;
  
  if (busyAtom.get()) { 
    queueAtom.set([...queueAtom.get(), trimmed]); 
    inputAtom.set(''); 
    statusAtom.set('queued'); 
    return; 
  }
  
  const submitted = await interpolateText(trimmed, gateway);
  
  appendTranscript(makeMessage('user', submitted));
  addToHistory(submitted);
  scrollOffsetAtom.set(0); 
  inputAtom.set(''); 
  completionItemsAtom.set([]);
  busyAtom.set(true); 
  statusAtom.set('running');
  
  try { 
    await gateway.request('prompt.submit', { 
      session_id: sessionInfoAtom.get()?.id, 
      text: submitted 
    }); 
  } catch (error) { 
    appendSystem(error instanceof Error ? error.message : String(error)); 
    busyAtom.set(false); 
    statusAtom.set('error'); 
  }
}

async function answerApprovalOverlay(gateway: GatewayClient): Promise<void> {
  const ov = overlayAtom.get();
  if (ov.type !== 'approval') return;
  
  const decision = APPROVAL_CHOICES[ov.selected] || 'deny';
  const response = await gateway.request<{ 
    executed?: { 
      method?: string; 
      result?: unknown 
    } 
  }>('approval.respond', { 
    request_id: ov.request_id, 
    decision 
  });
  
  if (response.executed) {
    appendSystem(formatNaturalResult({ 
      method: response.executed.method, 
      result: response.executed.result 
    }));
  }
  
  closeOverlay();
}

async function answerClarifyOverlay(gateway: GatewayClient): Promise<void> {
  const ov = overlayAtom.get();
  if (ov.type !== 'clarify') return;
  
  const answer = ov.freeText || !ov.choices ? ov.value : ov.choices[ov.selected];
  const response = await gateway.request<{ 
    executed?: { 
      method?: string; 
      result?: unknown 
    } 
  }>('clarify.respond', { 
    request_id: ov.request_id, 
    answer 
  });
  
  if (response.executed) {
    appendSystem(formatNaturalResult({ 
      method: response.executed.method, 
      result: response.executed.result 
    }));
  }
  
  closeOverlay();
}

async function answerSessionPickerOverlay(gateway: GatewayClient): Promise<void> {
  const ov = overlayAtom.get();
  if (ov.type !== 'sessionPicker') return;
  
  const selected = ov.sessions[ov.selected];
  
  if (selected) { 
    const result = await gateway.request<{ 
      messages?: Array<{ 
        role: TranscriptMessage['role']; 
        text?: string 
      }> 
    }>('session.resume', { 
      session_id: selected.id 
    });
    
    transcriptAtom.set(
      (result.messages || []).map(item => 
        makeMessage(item.role || 'system', item.text || '')
      )
    );
    
    scrollOffsetAtom.set(0); 
  }
  
  closeOverlay();
}

async function answerModelPickerOverlay(gateway: GatewayClient): Promise<void> {
  const ov = overlayAtom.get();
  if (ov.type !== 'modelPicker') return;
  
  const selected = ov.providers[ov.selected];
  
  if (selected) { 
    overlayAtom.set({ 
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
    closeOverlay(); 
  }
}

async function answerModelSetupOverlay(gateway: GatewayClient): Promise<void> {
  const ov = overlayAtom.get();
  if (ov.type !== 'modelSetup') return;
  
  const next = advanceModelSetupOverlay(ov);
  
  if (next.type === 'modelSetup') { 
    overlayAtom.set(next); 
    return; 
  }
  
  const configured = await gateway.request<{ 
    ok?: boolean; 
    provider?: string; 
    model?: string; 
    base_url?: string; 
    health?: { 
      status?: string 
    } 
  }>('model.setup', { 
    provider: ov.provider.slug, 
    base_url: next.values.base_url, 
    api_key_env: next.values.api_key_env, 
    api_key: next.values.api_key, 
    model: next.values.model 
  });
  
  appendSystem(
    configured.ok 
      ? `模型已配置：${configured.model} (${configured.health?.status || configured.provider})` 
      : `模型提供方：${ov.provider.name}`
  );
  
  closeOverlay();
}

export async function answerOverlay(gateway: GatewayClient) {
  const ov = overlayAtom.get();
  
  switch (ov.type) {
    case 'approval':
      await answerApprovalOverlay(gateway);
      break;
    case 'clarify':
      await answerClarifyOverlay(gateway);
      break;
    case 'sudo':
      await gateway.request('sudo.respond', { 
        request_id: ov.request_id, 
        value: ov.value 
      }); 
      closeOverlay();
      break;
    case 'secret':
      await gateway.request('secret.respond', { 
        request_id: ov.request_id, 
        value: ov.value 
      }); 
      closeOverlay();
      break;
    case 'sessionPicker':
      await answerSessionPickerOverlay(gateway);
      break;
    case 'modelPicker':
      await answerModelPickerOverlay(gateway);
      break;
    case 'modelSetup':
      await answerModelSetupOverlay(gateway);
      break;
  }
}

export async function answerOverlayWithChoice(choice: string, gateway: GatewayClient) {
  const ov = overlayAtom.get();
  
  if (ov.type === 'approval') {
    const response = await gateway.request<{ 
      executed?: { 
        method?: string; 
        result?: unknown 
      } 
    }>('approval.respond', { 
      request_id: ov.request_id, 
      decision: choice 
    });
    
    if (response.executed) {
      appendSystem(
        formatNaturalResult({ 
          method: response.executed.method, 
          result: response.executed.result 
        })
      );
    }
    
    closeOverlay();
  } else {
    await answerOverlay(gateway);
  }
}

const isPathCompletion = (text: string) => /(^|\s)(@|\.\/|\.\.\/|~\/|\/)[^\s]*$/.test(text);

export async function requestCompletion(value: string, gateway: GatewayClient) {
  if (!value.trim()) { 
    completionItemsAtom.set([]); 
    return; 
  }
  
  const method = value.startsWith('/') 
    ? 'complete.slash' 
    : isPathCompletion(value) 
      ? 'complete.path' 
      : '';
  
  if (!method) { 
    completionItemsAtom.set([]); 
    return; 
  }
  
  try { 
    const result = await gateway.request<{ 
      items?: import('../types.js').CompletionItem[]; 
      replace_from?: number 
    }>(method, { 
      session_id: sessionInfoAtom.get()?.id, 
      text: value 
    });
    
    completionItemsAtom.set(result.items || []); 
    completionIndexAtom.set(0); 
    replaceFromAtom.set(result.replace_from ?? 0); 
  } catch { 
    completionItemsAtom.set([]); 
  }
}

export function applyCompletionText(text: string, completion: string) {
  const start = completion.startsWith('/') && text.startsWith('/') && replaceFromAtom.get() === 1 
    ? 0 
    : replaceFromAtom.get();
  
  return `${text.slice(0, Math.max(0, start))}${completion}`;
}

export function drainQueue(gateway: GatewayClient) {
  const q = queueAtom.get();
  
  if (!q.length) return;
  
  const [next, ...rest] = q;
  queueAtom.set(rest);
  
  if (next) {
    setTimeout(() => void submitPrompt(next, gateway), 0);
  }
}
