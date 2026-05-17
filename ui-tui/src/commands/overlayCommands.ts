import type { GatewayClient } from '../gatewayClient.js';
import type { OverlayState } from '../types.js';
import { overlayAtom, closeOverlay } from '../stores/overlayStore.js';
import { answerOverlay, answerOverlayWithChoice } from '../handlers/promptHandler.js';
import { APPROVAL_CHOICES, QUICK_APPROVAL_MAP } from '../constants.js';
import type { CommandHandler } from './keyboardCommands.js';

/**
 * Escape键关闭覆盖层命令
 */
export const handleOverlayEscape: CommandHandler = ({ key }) => {
  if (!key.escape) return false;
  
  closeOverlay();
  return true;
};

/**
 * Enter键提交覆盖层命令
 */
export const handleOverlaySubmit: CommandHandler = (context) => {
  if (!context.key.return) return false;
  
  void answerOverlay(context.gateway);
  return true;
};

/**
 * 上下箭头导航命令
 */
export const handleOverlayNavigation: CommandHandler = ({ key }) => {
  if (!key.upArrow && !key.downArrow) return false;
  
  const direction = key.upArrow ? -1 : 1;
  const ov = overlayAtom.get();
  
  if (ov.type === 'approval') {
    const newIndex = Math.max(0, Math.min(APPROVAL_CHOICES.length - 1, ov.selected + direction));
    overlayAtom.set({ ...ov, selected: newIndex });
  } else if (ov.type === 'clarify' && ov.choices) {
    const newIndex = Math.max(0, Math.min(ov.choices.length - 1, ov.selected + direction));
    overlayAtom.set({ ...ov, selected: newIndex });
  } else if (ov.type === 'sessionPicker') {
    const newIndex = Math.max(0, Math.min(ov.sessions.length - 1, ov.selected + direction));
    overlayAtom.set({ ...ov, selected: newIndex });
  } else if (ov.type === 'modelPicker') {
    const newIndex = Math.max(0, Math.min(ov.providers.length - 1, ov.selected + direction));
    overlayAtom.set({ ...ov, selected: newIndex });
  }
  
  return true;
};

/**
 * 快速审批命令（o/s/a/d键）
 */
export const handleQuickApproval: CommandHandler = (context) => {
  const ov = overlayAtom.get();
  
  if (ov.type !== 'approval' || !['o', 's', 'a', 'd'].includes(context.value)) {
    return false;
  }
  
  const choice = QUICK_APPROVAL_MAP[context.value];
  void answerOverlayWithChoice(choice, context.gateway);
  return true;
};

/**
 * 数字选择命令（澄清问题时使用1-9键）
 */
export const handleNumericSelection: CommandHandler = ({ value }) => {
  const ov = overlayAtom.get();
  
  if (ov.type !== 'clarify' || !ov.choices || !/^[1-9]$/.test(value)) {
    return false;
  }
  
  const selected = Number.parseInt(value, 10) - 1;
  
  if (selected >= 0 && selected < ov.choices.length) {
    overlayAtom.set({ ...ov, selected });
    setTimeout(() => void answerOverlay({} as GatewayClient), 0);
  }
  
  return true;
};

/**
 * 退格/删除键处理命令
 */
export const handleBackspaceDelete: CommandHandler = ({ key }) => {
  if (!key.backspace && !key.delete) return false;
  
  const ov = overlayAtom.get();
  
  if (ov.type === 'secret' || ov.type === 'sudo') {
    overlayAtom.set({ ...ov, value: ov.value.slice(0, -1) });
  } else if (ov.type === 'modelSetup') {
    overlayAtom.set({ ...ov, value: ov.value.slice(0, -1) });
  } else if (ov.type === 'clarify' && (ov.freeText || !ov.choices)) {
    overlayAtom.set({ ...ov, value: ov.value.slice(0, -1) });
  }
  
  return true;
};

/**
 * 文本输入命令（秘密、sudo、模型设置、澄清问题）
 */
export const handleTextInput: CommandHandler = ({ value }) => {
  if (!value) return false;
  
  const ov = overlayAtom.get();
  
  if (ov.type === 'secret' || ov.type === 'sudo') {
    overlayAtom.set({ ...ov, value: `${ov.value}${value}` });
    return true;
  }
  
  if (ov.type === 'modelSetup') {
    overlayAtom.set({ ...ov, value: `${ov.value}${value}` });
    return true;
  }
  
  if (ov.type === 'clarify' && (ov.freeText || !ov.choices)) {
    overlayAtom.set({ ...ov, value: `${ov.value}${value}` });
    return true;
  }
  
  return false;
};

/**
 * 覆盖层命令链
 */
export const overlayCommandChain: CommandHandler[] = [
  handleOverlayEscape,
  handleOverlaySubmit,
  handleOverlayNavigation,
  handleQuickApproval,
  handleNumericSelection,
  handleBackspaceDelete,
  handleTextInput,
];
