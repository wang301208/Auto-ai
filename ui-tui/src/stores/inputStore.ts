import { atom, computed } from 'nanostores';
import type { CompletionItem } from '../types.js';
import { HISTORY_CONFIG, INPUT_LIMITS } from '../constants.js';

export const inputAtom = atom('');
export const inputBufferAtom = atom<string[]>([]);
export const historyAtom = atom<string[]>([]);
export const queueAtom = atom<string[]>([]);
export const completionItemsAtom = atom<CompletionItem[]>([]);
export const completionIndexAtom = atom(0);
export const replaceFromAtom = atom(0);
export const scrollOffsetAtom = atom(0);
export const compactAtom = atom(false);
export const showDetailsAtom = atom(true);

export const composedInput = computed(
  [inputAtom, inputBufferAtom],
  (input, buffer) => buffer.length ? `${buffer.join('\n')}\n${input}` : input
);

export const queueCount = computed([queueAtom], q => q.length);

/**
 * 设置输入值（带长度限制）
 */
export function setInput(value: string): void {
  if (typeof value !== 'string') return;
  const limited = value.length > INPUT_LIMITS.MAX_LENGTH 
    ? value.slice(0, INPUT_LIMITS.MAX_LENGTH) 
    : value;
  inputAtom.set(limited);
}

/**
 * 添加多行输入（带行数限制）
 */
export function addInputLine(line: string): void {
  const buffer = inputBufferAtom.get();
  if (buffer.length >= INPUT_LIMITS.MAX_LINES) {
    buffer.shift();
  }
  inputBufferAtom.set([...buffer, line]);
}

/**
 * 添加历史记录（带去重和长度限制）
 */
export function addToHistory(text: string): void {
  if (typeof text !== 'string') return;
  if (!text.trim()) return;
  
  const currentHistory = historyAtom.get();
  const filtered = currentHistory.filter(item => item !== text);
  const newHistory = [text, ...filtered].slice(0, HISTORY_CONFIG.MAX_ITEMS);
  
  historyAtom.set(newHistory);
}

/**
 * 清空历史记录
 */
export function clearHistory(): void {
  historyAtom.set([]);
}
