import { describe, it, expect, beforeEach } from 'vitest';
import { atom } from 'nanostores';
import { transcriptAtom, streamingAtom, thinkingAtom, appendTranscript, clearTranscript, messageCount } from '../src/stores/transcriptStore.js';
import { overlayAtom, closeOverlay, isOverlayOpen } from '../src/stores/overlayStore.js';
import { busyAtom, statusAtom, sessionInfoAtom } from '../src/stores/sessionStore.js';
import { inputAtom, queueAtom, completionItemsAtom, scrollOffsetAtom } from '../src/stores/inputStore.js';

describe('transcriptStore', () => {
  beforeEach(() => { transcriptAtom.set([]); streamingAtom.set(''); thinkingAtom.set(''); });

  it('appendTranscript adds messages', () => {
    appendTranscript({ id: '1', role: 'user', text: 'hello', timestamp: Date.now() });
    expect(transcriptAtom.get()).toHaveLength(1);
    expect(transcriptAtom.get()[0].text).toBe('hello');
  });

  it('messageCount computed works', () => {
    expect(messageCount.get()).toBe(0);
    appendTranscript({ id: '1', role: 'user', text: 'a', timestamp: Date.now() });
    expect(messageCount.get()).toBe(1);
  });

  it('clearTranscript resets all', () => {
    streamingAtom.set('streaming');
    thinkingAtom.set('thinking');
    appendTranscript({ id: '1', role: 'system', text: 'x', timestamp: Date.now() });
    clearTranscript();
    expect(transcriptAtom.get()).toHaveLength(0);
    expect(streamingAtom.get()).toBe('');
    expect(thinkingAtom.get()).toBe('');
  });
});

describe('overlayStore', () => {
  beforeEach(() => { overlayAtom.set({ type: 'none' }); });

  it('closeOverlay sets type to none', () => {
    overlayAtom.set({ type: 'approval', selected: 0, timeout_remaining: 30 });
    closeOverlay();
    expect(overlayAtom.get().type).toBe('none');
  });

  it('isOverlayOpen detects correctly', () => {
    expect(isOverlayOpen()).toBe(false);
    overlayAtom.set({ type: 'approval', selected: 0, timeout_remaining: 30 });
    expect(isOverlayOpen()).toBe(true);
  });
});

describe('sessionStore', () => {
  beforeEach(() => { busyAtom.set(false); statusAtom.set('starting'); });

  it('busyAtom toggles', () => {
    busyAtom.set(true);
    expect(busyAtom.get()).toBe(true);
    busyAtom.set(false);
    expect(busyAtom.get()).toBe(false);
  });

  it('statusAtom updates', () => {
    statusAtom.set('ready');
    expect(statusAtom.get()).toBe('ready');
  });
});

describe('inputStore', () => {
  beforeEach(() => { inputAtom.set(''); queueAtom.set([]); scrollOffsetAtom.set(0); });

  it('inputAtom stores value', () => {
    inputAtom.set('hello');
    expect(inputAtom.get()).toBe('hello');
  });

  it('queueAtom manages items', () => {
    queueAtom.set(['a', 'b']);
    expect(queueAtom.get()).toHaveLength(2);
    const [next, ...rest] = queueAtom.get();
    queueAtom.set(rest);
    expect(queueAtom.get()).toHaveLength(1);
    expect(next).toBe('a');
  });

  it('scrollOffsetAtom clamps', () => {
    scrollOffsetAtom.set(5);
    expect(scrollOffsetAtom.get()).toBe(5);
    scrollOffsetAtom.set(0);
    expect(scrollOffsetAtom.get()).toBe(0);
  });
});
