import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { 
  handleTabCompletion,
  handleCompletionNavigation,
  handleClearScreen,
  handleScrolling,
  handleMultilineInput,
  handleContinuation,
  executeCommandChain,
  mainInputCommandChain,
  type CommandContext,
} from '../src/commands/keyboardCommands.js';
import { 
  inputAtom,
  inputBufferAtom,
  completionItemsAtom,
  completionIndexAtom,
  scrollOffsetAtom,
  queueAtom,
  showDetailsAtom,
} from '../src/stores/index.js';
import { transcriptAtom } from '../src/stores/transcriptStore.js';
import type { GatewayClient } from '../src/gatewayClient.js';

describe('keyboardCommands', () => {
  beforeEach(() => {
    inputAtom.set('');
    inputBufferAtom.set([]);
    completionItemsAtom.set([]);
    completionIndexAtom.set(0);
    scrollOffsetAtom.set(0);
    queueAtom.set([]);
    showDetailsAtom.set(true);
    transcriptAtom.set([]);
  });

  describe('handleTabCompletion', () => {
    it('applies completion when items exist', () => {
      completionItemsAtom.set([{ text: 'hello' }, { text: 'world' }]);
      completionIndexAtom.set(1);
      inputAtom.set('w');
      
      const result = handleTabCompletion({
        value: '\t',
        key: { tab: true },
        input: 'w',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(true);
      expect(inputAtom.get()).toBe('world');
      expect(completionItemsAtom.get()).toEqual([]);
    });

    it('returns false when no completion items', () => {
      const result = handleTabCompletion({
        value: '\t',
        key: { tab: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('handleCompletionNavigation', () => {
    it('navigates up in completion list', () => {
      completionItemsAtom.set([{ text: 'a' }, { text: 'b' }, { text: 'c' }]);
      completionIndexAtom.set(2);
      
      handleCompletionNavigation({
        value: '',
        key: { upArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(completionIndexAtom.get()).toBe(1);
    });

    it('navigates down in completion list', () => {
      completionItemsAtom.set([{ text: 'a' }, { text: 'b' }, { text: 'c' }]);
      completionIndexAtom.set(0);
      
      handleCompletionNavigation({
        value: '',
        key: { downArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(completionIndexAtom.get()).toBe(1);
    });

    it('respects boundaries', () => {
      completionItemsAtom.set([{ text: 'a' }]);
      completionIndexAtom.set(0);
      
      handleCompletionNavigation({
        value: '',
        key: { upArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(completionIndexAtom.get()).toBe(0);
    });

    it('returns false when no completion items', () => {
      const result = handleCompletionNavigation({
        value: '',
        key: { upArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('handleClearScreen', () => {
    it('clears all state on Ctrl+L', () => {
      transcriptAtom.set([{ id: '1', role: 'user', text: 'test', timestamp: Date.now() }]);
      scrollOffsetAtom.set(5);
      queueAtom.set(['msg1', 'msg2']);
      
      const result = handleClearScreen({
        value: 'l',
        key: { ctrl: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(true);
      expect(transcriptAtom.get()).toEqual([]);
      expect(scrollOffsetAtom.get()).toBe(0);
      expect(queueAtom.get()).toEqual([]);
    });

    it('returns false for other keys', () => {
      const result = handleClearScreen({
        value: 'x',
        key: { ctrl: false },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('handleScrolling', () => {
    it('scrolls up with up arrow', () => {
      transcriptAtom.set([
        { id: '1', role: 'user', text: 'msg1', timestamp: Date.now() },
        { id: '2', role: 'assistant', text: 'msg2', timestamp: Date.now() },
      ]);
      
      handleScrolling({
        value: '',
        key: { upArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(scrollOffsetAtom.get()).toBeGreaterThan(0);
    });

    it('scrolls down with down arrow', () => {
      scrollOffsetAtom.set(5);
      
      handleScrolling({
        value: '',
        key: { downArrow: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(scrollOffsetAtom.get()).toBeLessThan(5);
    });

    it('page up scrolls more', () => {
      transcriptAtom.set(Array.from({ length: 20 }, (_, i) => ({
        id: `${i}`,
        role: 'user',
        text: `msg${i}`,
        timestamp: Date.now(),
      })));
      
      handleScrolling({
        value: '',
        key: { pageUp: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(scrollOffsetAtom.get()).toBeGreaterThanOrEqual(12);
    });

    it('returns false when input is not empty', () => {
      inputAtom.set('test');
      
      const result = handleScrolling({
        value: '',
        key: { upArrow: true },
        input: 'test',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('handleMultilineInput', () => {
    it('adds current input to buffer on Meta+Enter', () => {
      inputAtom.set('line1');
      
      handleMultilineInput({
        value: '\r',
        key: { meta: true, return: true },
        input: 'line1',
        gateway: {} as GatewayClient,
      });
      
      expect(inputBufferAtom.get()).toEqual(['line1']);
      expect(inputAtom.get()).toBe('');
    });

    it('adds current input to buffer on Shift+Enter', () => {
      inputAtom.set('line1');
      
      handleMultilineInput({
        value: '\r',
        key: { shift: true, return: true },
        input: 'line1',
        gateway: {} as GatewayClient,
      });
      
      expect(inputBufferAtom.get()).toEqual(['line1']);
    });

    it('returns false for other key combinations', () => {
      const result = handleMultilineInput({
        value: '\r',
        key: { return: true },
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('handleContinuation', () => {
    it('handles backslash continuation', () => {
      inputAtom.set('command \\');
      
      handleContinuation({
        value: '\r',
        key: { return: true },
        input: 'command \\',
        gateway: {} as GatewayClient,
      });
      
      expect(inputBufferAtom.get()).toEqual(['command ']);
      expect(inputAtom.get()).toBe('');
    });

    it('returns false when input does not end with backslash', () => {
      inputAtom.set('command');
      
      const result = handleContinuation({
        value: '\r',
        key: { return: true },
        input: 'command',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('executeCommandChain', () => {
    it('executes first matching command', () => {
      let executed = false;
      const mockCommand = vi.fn(() => {
        executed = true;
        return true;
      });
      
      const result = executeCommandChain([mockCommand], {
        value: '',
        key: {},
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(true);
      expect(executed).toBe(true);
      expect(mockCommand).toHaveBeenCalled();
    });

    it('continues to next command if first returns false', () => {
      const firstCommand = vi.fn(() => false);
      const secondCommand = vi.fn(() => true);
      
      const result = executeCommandChain([firstCommand, secondCommand], {
        value: '',
        key: {},
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(true);
      expect(firstCommand).toHaveBeenCalled();
      expect(secondCommand).toHaveBeenCalled();
    });

    it('returns false when no commands match', () => {
      const command1 = vi.fn(() => false);
      const command2 = vi.fn(() => false);
      
      const result = executeCommandChain([command1, command2], {
        value: '',
        key: {},
        input: '',
        gateway: {} as GatewayClient,
      });
      
      expect(result).toBe(false);
    });
  });

  describe('mainInputCommandChain', () => {
    it('contains expected commands', () => {
      expect(mainInputCommandChain.length).toBeGreaterThan(0);
    });
  });
});
