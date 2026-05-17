import { KEY_SEQUENCES } from '../constants.js';
import { KeyType, type ParsedKey } from './types.js';

const KNOWN_CSI_SEQUENCES: ReadonlySet<string> = new Set([
  KEY_SEQUENCES.PAGE_UP_ALT,
  KEY_SEQUENCES.PAGE_UP_CTRL,
  KEY_SEQUENCES.PAGE_DOWN_ALT,
  KEY_SEQUENCES.PAGE_DOWN_3,
  KEY_SEQUENCES.UP_ARROW_SHIFT,
  KEY_SEQUENCES.UP_ARROW,
  KEY_SEQUENCES.DOWN_ARROW_SHIFT,
  KEY_SEQUENCES.DOWN_ARROW,
  KEY_SEQUENCES.LEFT_ARROW,
  KEY_SEQUENCES.RIGHT_ARROW,
  KEY_SEQUENCES.HOME,
  KEY_SEQUENCES.END,
  KEY_SEQUENCES.INSERT,
  KEY_SEQUENCES.DELETE,
]);

function isMouseEvent(seq: string): boolean {
  return seq.startsWith(KEY_SEQUENCES.MOUSE_PREFIX) ||
         seq.startsWith(KEY_SEQUENCES.MOUSE_CLICK_PREFIX) ||
         seq.startsWith(KEY_SEQUENCES.MOUSE_X10_EXT_PREFIX);
}

function parseMouseScroll(seq: string): { button: number; delta: number } | null {
  // SGR模式: ESC[<Cb;Cx;Cym (hex: 1b5b3c...)
  if (seq.startsWith('1b5b3c')) {
    const data = seq.slice(6);
    const semicolonIdx = data.indexOf('3b');
    if (semicolonIdx > 0) {
      const cbHex = data.slice(0, semicolonIdx);
      const cb = parseInt(cbHex, 16);
      const delta = cb === 64 ? -1 : cb === 65 ? 1 : 0;
      return { button: cb, delta };
    }
  }
  
  // X10扩展模式: ESC[M Cb Cx Cy (hex: 1b5b4d...)
  // Cb是字符编码，滚轮: 94('^')=向上, 97('a')=向下
  if (seq.startsWith('1b5b4d') && seq.length >= 8) {
    const cbHex = seq.slice(6, 8);
    const cb = parseInt(cbHex, 16);
    let delta = 0;
    if (cb === 94) delta = -1;
    else if (cb === 97) delta = 1;
    else {
      const buttonCode = cb - 32;
      if (buttonCode === 64 || buttonCode === 4) delta = -1;
      else if (buttonCode === 65 || buttonCode === 5) delta = 1;
    }
    return { button: cb, delta };
  }
  
  // 传统模式: ESC M Cb Cx Cy (hex: 1b4d...)
  if (seq.startsWith('1b4d') && seq.length >= 6) {
    const cbHex = seq.slice(4, 6);
    const cb = parseInt(cbHex, 16);
    const delta = cb === 64 ? -1 : cb === 65 ? 1 : 0;
    return { button: cb, delta };
  }
  
  return null;
}

function isUnknownCSI(seq: string): boolean {
  return seq.startsWith('1b5b') && seq.length > 4 && !KNOWN_CSI_SEQUENCES.has(seq);
}

function detectCtrlChar(seq: string): string | null {
  if (seq.length !== 2 || seq === '0d' || seq === '0a') {
    return null;
  }
  const code = parseInt(seq, 16);
  if (code > 0 && code < 32) {
    return String.fromCharCode(code + 96);
  }
  return null;
}

function isPrintableChar(char: string): boolean {
  return (
    char.length === 1 &&
    !/\p{C}/u.test(char) &&
    char.charCodeAt(0) >= 32 &&
    char.charCodeAt(0) <= 0x10FFFF
  );
}

function createMouseKey(seq: string, char: string): ParsedKey {
  const mouseData = parseMouseScroll(seq);
  
  return {
    seq,
    char,
    type: KeyType.MOUSE,
    isMouse: true,
    isCtrlC: false,
    isCtrlD: false,
    isEscape: false,
    isReturn: false,
    isBackspace: false,
    isTab: false,
    isUpArrow: false,
    isDownArrow: false,
    isPageUp: false,
    isPageDown: false,
    isDelete: false,
    isPrintable: false,
    ctrlChar: null,
    mouseButton: mouseData?.button,
    mouseDelta: mouseData?.delta,
  };
}

function createParsedKey(seq: string, char: string, flags: Partial<ParsedKey>): ParsedKey {
  const isPrintable = flags.isPrintable ?? isPrintableChar(char);
  const ctrlChar = flags.ctrlChar ?? detectCtrlChar(seq);
  
  let type = KeyType.UNKNOWN;
  if (flags.isCtrlC || flags.isCtrlD || flags.isReturn || flags.isBackspace || flags.isTab) {
    type = KeyType.CONTROL;
  } else if (flags.isUpArrow || flags.isDownArrow || flags.isPageUp || flags.isPageDown) {
    type = KeyType.NAVIGATION;
  } else if (isPrintable) {
    type = KeyType.PRINTABLE;
  }

  return {
    seq,
    char,
    type,
    isMouse: false,
    isCtrlC: flags.isCtrlC ?? false,
    isCtrlD: flags.isCtrlD ?? false,
    isEscape: flags.isEscape ?? false,
    isReturn: flags.isReturn ?? false,
    isBackspace: flags.isBackspace ?? false,
    isTab: flags.isTab ?? false,
    isUpArrow: flags.isUpArrow ?? false,
    isDownArrow: flags.isDownArrow ?? false,
    isPageUp: flags.isPageUp ?? false,
    isPageDown: flags.isPageDown ?? false,
    isDelete: flags.isDelete ?? false,
    isPrintable,
    ctrlChar,
  };
}

export function parseKey(chunk: Buffer): ParsedKey | null {
  const seq = chunk.toString('hex');
  const char = chunk.toString();

  if (isMouseEvent(seq)) {
    return createMouseKey(seq, char);
  }

  if (isUnknownCSI(seq)) {
    return null;
  }

  const isCtrlC = seq === KEY_SEQUENCES.CTRL_C;
  const isCtrlD = seq === KEY_SEQUENCES.CTRL_D;
  const isEscape = seq === KEY_SEQUENCES.ESCAPE;

  if (isEscape) {
    return null;
  }

  const key = createParsedKey(seq, char, {
    isCtrlC,
    isCtrlD,
    isEscape,
    isReturn: seq === '0d',
    isBackspace: seq === '7f' || seq === '08',
    isTab: seq === '09',
    isUpArrow: seq === KEY_SEQUENCES.UP_ARROW || seq === KEY_SEQUENCES.UP_ARROW_SHIFT,
    isDownArrow: seq === KEY_SEQUENCES.DOWN_ARROW || seq === KEY_SEQUENCES.DOWN_ARROW_SHIFT,
    isPageUp: seq === KEY_SEQUENCES.PAGE_UP_ALT || seq === KEY_SEQUENCES.PAGE_UP_CTRL,
    isPageDown: seq === KEY_SEQUENCES.PAGE_DOWN_ALT || seq === KEY_SEQUENCES.PAGE_DOWN_3,
    isDelete: seq === KEY_SEQUENCES.DELETE,
  });

  return key;
}

export { KNOWN_CSI_SEQUENCES };
