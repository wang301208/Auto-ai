import type { GatewayClient } from '../gatewayClient.js';
import type { ParsedKey, InputContext, InputHandler, RouterDeps, RouterConfig } from './types.js';
import type { KeyInfo, CommandContext } from '../commands/keyboardCommands.js';
import { overlayAtom, closeOverlay } from '../stores/overlayStore.js';
import { inputAtom, scrollOffsetAtom, completionItemsAtom, completionIndexAtom } from '../stores/inputStore.js';
import { transcriptAtom } from '../stores/transcriptStore.js';
import { sessionInfoAtom, busyAtom, statusAtom } from '../stores/sessionStore.js';
import { executeCommandChain, mainInputCommandChain, overlayCommandChain } from '../commands/index.js';
import { debugInputSequence } from '../utils/inputDebugger.js';
import { parseKey } from './keyParser.js';
import { defaultScrollHandler } from './scrollHandler.js';
import { SCROLL_CONFIG } from '../constants.js';

const ESCAPE_SEQUENCE_TIMEOUT_MS = 100;
const MAX_BUFFER_SIZE = 64;

function buildInputContext(): InputContext {
  return {
    input: inputAtom.get(),
    busy: busyAtom.get(),
    overlayOpen: overlayAtom.get().type !== 'none',
    hasCompletions: completionItemsAtom.get().length > 0,
  };
}

function handleCtrlC(key: ParsedKey, ctx: InputContext, deps: RouterDeps): boolean {
  if (!key.isCtrlC) return false;

  if (ctx.overlayOpen) {
    closeOverlay();
  } else if (ctx.busy) {
    void deps.gateway.request('session.interrupt', {
      session_id: sessionInfoAtom.get()?.id,
    });
    busyAtom.set(false);
    statusAtom.set('interrupted');
  } else if (ctx.input) {
    inputAtom.set('');
  } else {
    deps.gateway.stop();
    deps.exitApp();
  }
  
  return true;
}

function handleCtrlD(key: ParsedKey, ctx: InputContext, deps: RouterDeps): boolean {
  if (!key.isCtrlD) return false;
  
  deps.gateway.stop();
  deps.exitApp();
  return true;
}

function handleOverlayInput(key: ParsedKey, ctx: InputContext, deps: RouterDeps): boolean {
  if (!ctx.overlayOpen) return false;

  const keyInfo: KeyInfo = {
    escape: false,
    return: key.isReturn,
    upArrow: key.isUpArrow,
    downArrow: key.isDownArrow,
    backspace: key.isBackspace,
    delete: key.isDelete,
  };

  executeCommandChain(overlayCommandChain, {
    value: key.char,
    key: keyInfo,
    input: ctx.input,
    gateway: deps.gateway,
  });
  
  return true;
}

function handleScrollInput(key: ParsedKey, ctx: InputContext): boolean {
  const shouldScroll = 
    (!ctx.hasCompletions && (key.isPageUp || key.isPageDown || key.isUpArrow || key.isDownArrow)) ||
    (ctx.hasCompletions && (key.isPageUp || key.isPageDown));

  if (!shouldScroll) return false;

  const state = {
    offset: scrollOffsetAtom.get(),
    max: transcriptAtom.get().length,
  };

  let newOffset: number;
  if (key.isPageUp) {
    newOffset = defaultScrollHandler.handlePageUp(state);
  } else if (key.isPageDown) {
    newOffset = defaultScrollHandler.handlePageDown(state);
  } else if (key.isUpArrow) {
    newOffset = defaultScrollHandler.handleLineUp(state);
  } else {
    newOffset = defaultScrollHandler.handleLineDown(state);
  }

  scrollOffsetAtom.set(newOffset);
  return true;
}

function handleMouseScroll(key: ParsedKey, ctx: InputContext): boolean {
  if (!key.isMouse || !key.mouseDelta) return false;
  
  // 补全列表时，鼠标滚动选择补全项
  if (ctx.hasCompletions) {
    const items = completionItemsAtom.get();
    if (!items.length) return false;
    
    const currentIndex = completionIndexAtom.get();
    const newIndex = key.mouseDelta < 0 
      ? Math.max(0, currentIndex - 1)
      : Math.min(items.length - 1, currentIndex + 1);
    completionIndexAtom.set(newIndex);
    return true;
  }
  
  // 无补全时，滚动消息历史
  const state = {
    offset: scrollOffsetAtom.get(),
    max: transcriptAtom.get().length,
  };
  
  const delta = key.mouseDelta * SCROLL_CONFIG.MOUSE_DELTA;
  const newOffset = defaultScrollHandler.handleDelta(state, delta);
  scrollOffsetAtom.set(newOffset);
  return true;
}

function handleMainInput(key: ParsedKey, ctx: InputContext, deps: RouterDeps): void {
  // Backspace 删除最后一个字符
  if (key.isBackspace && ctx.input.length > 0) {
    inputAtom.set(ctx.input.slice(0, -1));
    return;
  }

  // Delete 键删除光标后字符（这里简化为删除最后一个字符）
  if (key.isDelete && ctx.input.length > 0) {
    inputAtom.set(ctx.input.slice(0, -1));
    return;
  }

  const keyInfo: KeyInfo = {
    tab: key.isTab,
    upArrow: key.isUpArrow,
    downArrow: key.isDownArrow,
    pageUp: key.isPageUp,
    pageDown: key.isPageDown,
    ctrl: key.ctrlChar !== null,
    meta: false,
    shift: false,
    return: key.isReturn,
    escape: false,
    backspace: key.isBackspace,
    delete: key.isDelete,
  };

  const cmdCtx: CommandContext = {
    value: key.char,
    key: keyInfo,
    input: ctx.input,
    gateway: deps.gateway,
  };

  const handled = executeCommandChain(mainInputCommandChain, cmdCtx);

  if (!handled && key.isPrintable) {
    inputAtom.set(ctx.input + key.char);
  }
}

export function createInputRouter(
  deps: RouterDeps,
  config: RouterConfig = {}
): (chunk: Buffer) => void {
  const debugEnabled = config.debugInput ?? !!process.env.DEBUG_INPUT;

  const handlers: InputHandler[] = [
    (key, ctx) => handleCtrlC(key, ctx, deps),
    (key, ctx) => handleCtrlD(key, ctx, deps),
    (key, ctx) => handleOverlayInput(key, ctx, deps),
    (key, ctx) => handleMouseScroll(key, ctx),
    (key, ctx) => handleScrollInput(key, ctx),
  ];

  let buffer: Buffer = Buffer.alloc(0);
  let bufferTimer: NodeJS.Timeout | null = null;

  function clearBuffer(): void {
    buffer = Buffer.alloc(0);
    if (bufferTimer) {
      clearTimeout(bufferTimer);
      bufferTimer = null;
    }
  }

  function flushBuffer(): Buffer {
    const data = buffer;
    clearBuffer();
    return data;
  }

  function startBufferTimer(): void {
    if (bufferTimer) clearTimeout(bufferTimer);
    bufferTimer = setTimeout(() => {
      const data = flushBuffer();
      if (data.length > 0) {
        routeChunk(data);
      }
    }, ESCAPE_SEQUENCE_TIMEOUT_MS);
  }

  function isEscapeSequence(data: Buffer): boolean {
    if (data.length === 0) return false;
    return data[0] === 0x1b;
  }

  function isSequenceComplete(data: Buffer): boolean {
    if (data.length === 0) return true;
    if (data[0] !== 0x1b) return true;
    if (data.length === 1) return false;
    if (data[1] === 0x5b) {
      const hex = data.toString('hex');
      if (hex.startsWith('1b5b4d')) return data.length >= 6;
      if (hex.startsWith('1b5b3c')) {
        const mCount = (data.toString().match(/;/g) || []).length;
        return mCount >= 2 && data[data.length - 1] === 0x6d;
      }
      return data.length >= 3;
    }
    if (data[1] === 0x4d) return data.length >= 4;
    if (data[1] === 0x4f) return data.length >= 3;
    return true;
  }

  function routeChunk(chunk: Buffer): void {
    const key = parseKey(chunk);
    if (!key) return;

    const ctx = buildInputContext();

    if (key.isMouse && !key.mouseDelta) return;

    for (const handler of handlers) {
      if (handler(key, ctx)) {
        return;
      }
    }

    handleMainInput(key, ctx, deps);
  }

  return function routeInput(chunk: Buffer): void {
    debugInputSequence(chunk, debugEnabled);

    if (buffer.length > 0) {
      buffer = Buffer.concat([buffer, chunk]);
      if (buffer.length > MAX_BUFFER_SIZE) {
        clearBuffer();
        return;
      }
      if (isSequenceComplete(buffer)) {
        const data = flushBuffer();
        routeChunk(data);
      } else {
        startBufferTimer();
      }
      return;
    }

    if (isEscapeSequence(chunk) && !isSequenceComplete(chunk)) {
      buffer = chunk;
      startBufferTimer();
      return;
    }

    routeChunk(chunk);
  };
}
