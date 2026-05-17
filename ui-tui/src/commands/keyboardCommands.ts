import type { GatewayClient } from '../gatewayClient.js';
import { 
  inputAtom, 
  inputBufferAtom, 
  completionItemsAtom, 
  completionIndexAtom, 
  scrollOffsetAtom, 
  queueAtom,
  showDetailsAtom,
} from '../stores/index.js';
import { transcriptAtom, clearTranscript } from '../stores/transcriptStore.js';
import { clearRuntime } from '../stores/runtimeStore.js';
import { applyCompletionText } from '../handlers/promptHandler.js';
import { SCROLL_CONFIG } from '../constants.js';

export interface KeyInfo {
  tab?: boolean;
  upArrow?: boolean;
  downArrow?: boolean;
  pageUp?: boolean;
  pageDown?: boolean;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  return?: boolean;
  escape?: boolean;
  backspace?: boolean;
  delete?: boolean;
}

export interface CommandContext {
  value: string;
  key: KeyInfo;
  input: string;
  gateway: GatewayClient;
}

export type CommandHandler = (ctx: CommandContext) => boolean;

/**
 * Tab键补全命令
 */
export const handleTabCompletion: CommandHandler = ({ key }) => {
  if (!key.tab) return false;
  
  const items = completionItemsAtom.get();
  const idx = completionIndexAtom.get();
  
  if (!items.length || idx < 0 || idx >= items.length) {
    completionItemsAtom.set([]);
    completionIndexAtom.set(0);
    return false;
  }
  
  const item = items[idx];
  inputAtom.set(applyCompletionText(inputAtom.get(), item.text));
  completionItemsAtom.set([]);
  completionIndexAtom.set(0);
  return true;
};

/**
 * 上下箭头选择补全项命令
 */
export const handleCompletionNavigation: CommandHandler = ({ key }) => {
  const cItems = completionItemsAtom.get();
  
  if (!cItems.length || (!key.upArrow && !key.downArrow)) {
    return false;
  }
  
  const currentIndex = completionIndexAtom.get();
  const newIndex = key.upArrow 
    ? Math.max(0, currentIndex - 1)
    : Math.min(cItems.length - 1, currentIndex + 1);
  
  completionIndexAtom.set(newIndex);
  return true;
};

/**
 * Ctrl+L清屏命令
 */
export const handleClearScreen: CommandHandler = ({ key, value }) => {
  if (!(key.ctrl && value === 'l')) return false;
  
  clearTranscript();
  scrollOffsetAtom.set(0);
  queueAtom.set([]);
  clearRuntime();
  
  return true;
};

/**
 * 滚动命令（无补全列表时）
 */
export const handleScrolling: CommandHandler = ({ key }) => {
  const cItems = completionItemsAtom.get();
  const input = inputAtom.get();
  
  if (cItems.length || input.length > 0 || 
      (!key.upArrow && !key.downArrow && !key.pageUp && !key.pageDown)) {
    return false;
  }
  
  const delta = key.pageUp 
    ? SCROLL_CONFIG.PAGE 
    : key.pageDown 
      ? -SCROLL_CONFIG.PAGE 
      : key.upArrow 
        ? SCROLL_CONFIG.STEP 
        : -SCROLL_CONFIG.STEP;
  
  const transcript = transcriptAtom.get();
  const len = transcript.length;
  
  if (len === 0) return false;
  
  const currentOffset = scrollOffsetAtom.get();
  const maxOffset = Math.max(0, len - 1);
  const clampedCurrent = Math.max(0, Math.min(maxOffset, currentOffset));
  const newOffset = Math.round(Math.max(0, Math.min(maxOffset, clampedCurrent + delta)));
  
  scrollOffsetAtom.set(newOffset);
  return true;
};

/**
 * 多行输入命令（Meta/Shift + Enter）
 */
export const handleMultilineInput: CommandHandler = ({ key }) => {
  if (!((key.meta || key.shift) && key.return)) return false;
  
  const currentInput = inputAtom.get();
  inputBufferAtom.set([...inputBufferAtom.get(), currentInput]);
  inputAtom.set('');
  
  return true;
};

/**
 * 续行符处理命令（反斜杠结尾）
 */
export const handleContinuation: CommandHandler = ({ key, input }) => {
  if (!(key.return && input.endsWith('\\'))) return false;
  
  inputBufferAtom.set([...inputBufferAtom.get(), input.slice(0, -1)]);
  inputAtom.set('');
  
  return true;
};

/**
 * 切换详情显示命令
 */
export const handleToggleDetails: CommandHandler = ({ key, value }) => {
  if (!(key.ctrl && value === 'd')) return false;
  
  showDetailsAtom.set(!showDetailsAtom.get());
  return true;
};

/**
 * 主输入区域命令链
 */
export const mainInputCommandChain: CommandHandler[] = [
  handleTabCompletion,
  handleCompletionNavigation,
  handleClearScreen,
  handleToggleDetails,
  handleScrolling,
  handleMultilineInput,
  handleContinuation,
];

/**
 * 执行命令链
 */
export function executeCommandChain(
  commands: CommandHandler[],
  context: CommandContext
): boolean {
  for (const command of commands) {
    if (command(context)) {
      return true;
    }
  }
  return false;
}
