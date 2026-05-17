import { describe, it, expect, beforeEach, vi } from 'vitest';
import { formatNaturalResult, applyCompletionText, drainQueue } from '../src/handlers/promptHandler.js';
import { executeCommandChain, overlayCommandChain, mainInputCommandChain, type KeyInfo } from '../src/commands/index.js';
import { overlayAtom, closeOverlay } from '../src/stores/overlayStore.js';
import { inputAtom, inputBufferAtom, completionItemsAtom, completionIndexAtom, replaceFromAtom, scrollOffsetAtom, queueAtom } from '../src/stores/inputStore.js';
import { transcriptAtom, clearTranscript } from '../src/stores/transcriptStore.js';
import { busyAtom } from '../src/stores/sessionStore.js';

describe('promptHandler', () => {
  describe('formatNaturalResult', () => {
    it('formats null result', () => {
      expect(formatNaturalResult({ method: 'test' })).toBe('test: 已完成');
    });

    it('formats string result', () => {
      expect(formatNaturalResult({ method: 'cmd', result: 'ok' })).toBe('cmd: ok');
    });

    it('formats object result', () => {
      const result = formatNaturalResult({ method: 'm', result: { a: 1 } });
      expect(result).toContain('m');
      expect(result).toContain('"a"');
    });

    it('uses command as label fallback', () => {
      expect(formatNaturalResult({ command: 'ls', result: 'files' })).toBe('ls: files');
    });

    it('uses default label', () => {
      expect(formatNaturalResult({ result: 42 })).toBe('自然语言命令: 42');
    });
  });

  describe('applyCompletionText', () => {
    beforeEach(() => { replaceFromAtom.set(0); });

    it('replaces from position 0', () => {
      replaceFromAtom.set(0);
      expect(applyCompletionText('/he', '/help')).toBe('/help');
    });

    it('replaces from mid position', () => {
      replaceFromAtom.set(5);
      expect(applyCompletionText('hello world', 'foo')).toBe('hellofoo');
    });
  });

  describe('drainQueue', () => {
    beforeEach(() => { queueAtom.set([]); busyAtom.set(false); });

    it('does nothing on empty queue', () => {
      const gw = { request: vi.fn() } as any;
      drainQueue(gw);
      expect(gw.request).not.toHaveBeenCalled();
    });

    it('dequeues first item', () => {
      queueAtom.set(['a', 'b']);
      const gw = { request: vi.fn().mockResolvedValue({}) } as any;
      drainQueue(gw);
      expect(queueAtom.get()).toEqual(['b']);
    });
  });
});

describe('overlayCommandChain', () => {
  const gw = { request: vi.fn().mockResolvedValue({}) } as any;

  beforeEach(() => { overlayAtom.set({ type: 'none' }); });

  it('escape closes overlay', () => {
    overlayAtom.set({ type: 'approval', selected: 0, timeout_remaining: 30 });
    executeCommandChain(overlayCommandChain, { value: '', key: { escape: true } as KeyInfo, input: '', gateway: gw });
    expect(overlayAtom.get().type).toBe('none');
  });

  it('upArrow changes approval selection', () => {
    overlayAtom.set({ type: 'approval', selected: 2, timeout_remaining: 30 });
    executeCommandChain(overlayCommandChain, { value: '', key: { upArrow: true } as KeyInfo, input: '', gateway: gw });
    expect((overlayAtom.get() as any).selected).toBe(1);
  });

  it('downArrow changes approval selection', () => {
    overlayAtom.set({ type: 'approval', selected: 1, timeout_remaining: 30 });
    executeCommandChain(overlayCommandChain, { value: '', key: { downArrow: true } as KeyInfo, input: '', gateway: gw });
    expect((overlayAtom.get() as any).selected).toBe(2);
  });

  it('backspace on secret overlay deletes last char', () => {
    overlayAtom.set({ type: 'secret', request_id: 'r1', env_var: 'KEY', prompt: 'p', value: 'abc' });
    executeCommandChain(overlayCommandChain, { value: '', key: { backspace: true } as KeyInfo, input: '', gateway: gw });
    expect((overlayAtom.get() as any).value).toBe('ab');
  });

  it('typing on secret overlay appends char', () => {
    overlayAtom.set({ type: 'secret', request_id: 'r1', env_var: 'KEY', prompt: 'p', value: 'ab' });
    executeCommandChain(overlayCommandChain, { value: 'c', key: {} as KeyInfo, input: '', gateway: gw });
    expect((overlayAtom.get() as any).value).toBe('abc');
  });

  it('typing on modelSetup overlay appends char', () => {
    const overlay = {
      type: 'modelSetup' as const,
      provider: { slug: 'test', name: 'Test', models: [] } as any,
      step: 'base_url' as const,
      values: { base_url: '', api_key_env: '', api_key: '', model: '' },
      value: 'https://'
    };
    overlayAtom.set(overlay);
    executeCommandChain(overlayCommandChain, { value: 'a', key: {} as KeyInfo, input: '', gateway: gw });
    expect((overlayAtom.get() as any).value).toBe('https://a');
  });

  it('return calls answerOverlay', () => {
    overlayAtom.set({ type: 'approval', selected: 0, timeout_remaining: 30 });
    const result = executeCommandChain(overlayCommandChain, { value: '', key: { return: true } as KeyInfo, input: '', gateway: gw });
    expect(result).toBe(true);
  });
});

describe('mainInputCommandChain', () => {
  const gw = { request: vi.fn().mockResolvedValue({}) } as any;

  beforeEach(() => {
    inputAtom.set('');
    inputBufferAtom.set([]);
    completionItemsAtom.set([]);
    completionIndexAtom.set(0);
    scrollOffsetAtom.set(0);
    queueAtom.set([]);
    transcriptAtom.set([]);
  });

  it('tab applies completion', () => {
    completionItemsAtom.set([{ text: '/help', display: '/help' }]);
    completionIndexAtom.set(0);
    inputAtom.set('/he');
    replaceFromAtom.set(0);
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { tab: true } as KeyInfo, input: '/he', gateway: gw });
    expect(result).toBe(true);
    expect(inputAtom.get()).toBe('/help');
  });

  it('Ctrl+L clears transcript and resets', () => {
    transcriptAtom.set([{ id: '1', role: 'system' as const, text: 'msg', timestamp: 1 }]);
    scrollOffsetAtom.set(5);
    const result = executeCommandChain(mainInputCommandChain, { value: 'l', key: { ctrl: true } as KeyInfo, input: '', gateway: gw });
    expect(result).toBe(true);
    expect(transcriptAtom.get()).toHaveLength(0);
    expect(scrollOffsetAtom.get()).toBe(0);
  });

  it('upArrow scrolls when no input and no completions', () => {
    transcriptAtom.set(Array.from({ length: 10 }, (_, i) => ({ id: `${i}`, role: 'user' as const, text: `${i}`, timestamp: i })));
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { upArrow: true } as KeyInfo, input: '', gateway: gw });
    expect(result).toBe(true);
    expect(scrollOffsetAtom.get()).toBe(3);
  });

  it('pageUp scrolls by page size', () => {
    transcriptAtom.set(Array.from({ length: 20 }, (_, i) => ({ id: `${i}`, role: 'user' as const, text: `${i}`, timestamp: i })));
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { pageUp: true } as KeyInfo, input: '', gateway: gw });
    expect(result).toBe(true);
    expect(scrollOffsetAtom.get()).toBe(12);
  });

  it('meta+return adds to inputBuffer', () => {
    inputAtom.set('line1');
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { meta: true, return: true } as KeyInfo, input: 'line1', gateway: gw });
    expect(result).toBe(true);
    expect(inputBufferAtom.get()).toEqual(['line1']);
    expect(inputAtom.get()).toBe('');
  });

  it('return with trailing backslash adds to buffer', () => {
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { return: true } as KeyInfo, input: 'line1\\', gateway: gw });
    expect(result).toBe(true);
    expect(inputBufferAtom.get()).toEqual(['line1']);
  });

  it('returns false for unhandled input', () => {
    const result = executeCommandChain(mainInputCommandChain, { value: 'a', key: {} as KeyInfo, input: 'hello', gateway: gw });
    expect(result).toBe(false);
  });

  it('upArrow cycles completion index when items exist', () => {
    completionItemsAtom.set([{ text: 'a', display: 'a' }, { text: 'b', display: 'b' }]);
    completionIndexAtom.set(0);
    const result = executeCommandChain(mainInputCommandChain, { value: '', key: { downArrow: true } as KeyInfo, input: 'test', gateway: gw });
    expect(result).toBe(true);
    expect(completionIndexAtom.get()).toBe(1);
  });
});
