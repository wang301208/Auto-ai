import { describe, it, expect, beforeEach } from 'vitest';
import { emotionAtom, suggestionsAtom, emotionLabel, emotionEmoji, activeSuggestions, setEmotion, addSuggestion, dismissSuggestion, clearSuggestions, EMOTION_META, type EmotionType } from '../src/stores/emotionStore.js';

describe('emotionStore', () => {
  beforeEach(() => {
    emotionAtom.set({ current: 'neutral', intensity: 0.3, confidence: 0.5, reason: '系统启动', since: Date.now(), history: [] });
    suggestionsAtom.set([]);
  });

  describe('EMOTION_META', () => {
    it('has 8 emotion types', () => {
      expect(Object.keys(EMOTION_META)).toHaveLength(8);
    });

    it('each emotion has emoji, label, color, description', () => {
      for (const [type, meta] of Object.entries(EMOTION_META)) {
        expect(meta.emoji).toBeTruthy();
        expect(meta.label).toBeTruthy();
        expect(meta.color).toBeTruthy();
        expect(meta.description).toBeTruthy();
      }
    });
  });

  describe('setEmotion', () => {
    it('transitions from neutral to curious', () => {
      setEmotion('curious', 0.8, '发现新信息');
      expect(emotionAtom.get().current).toBe('curious');
      expect(emotionAtom.get().intensity).toBe(0.8);
      expect(emotionAtom.get().reason).toBe('发现新信息');
    });

    it('records transition history', () => {
      setEmotion('curious', 0.7, 'explore');
      setEmotion('focused', 0.8, 'deep dive');
      expect(emotionAtom.get().history).toHaveLength(2);
      expect(emotionAtom.get().history[0].from).toBe('neutral');
      expect(emotionAtom.get().history[0].to).toBe('curious');
      expect(emotionAtom.get().history[1].from).toBe('curious');
      expect(emotionAtom.get().history[1].to).toBe('focused');
    });

    it('clamps intensity to 0-1', () => {
      setEmotion('confident', 1.5, 'test');
      expect(emotionAtom.get().intensity).toBe(1);
      setEmotion('confident', -0.5, 'test');
      expect(emotionAtom.get().intensity).toBe(0);
    });

    it('updates confidence when provided', () => {
      setEmotion('confident', 0.8, 'sure', 0.95);
      expect(emotionAtom.get().confidence).toBe(0.95);
    });

    it('preserves confidence when not provided', () => {
      emotionAtom.set({ ...emotionAtom.get(), confidence: 0.6 });
      setEmotion('focused', 0.7, 'test');
      expect(emotionAtom.get().confidence).toBe(0.6);
    });

    it('skips if same emotion with similar intensity', () => {
      setEmotion('curious', 0.7, 'first');
      const hist1 = emotionAtom.get().history.length;
      setEmotion('curious', 0.72, 'second');
      expect(emotionAtom.get().history.length).toBe(hist1);
    });

    it('blocks invalid transitions', () => {
      setEmotion('curious', 0.7, 'ok');
      setEmotion('frustrated', 0.8, 'blocked - curious cannot go directly to frustrated');
      expect(emotionAtom.get().current).toBe('curious');
    });

    it('limits history to 20 entries', () => {
      for (let i = 0; i < 25; i++) {
        const targets: EmotionType[] = ['curious', 'focused', 'creative'];
        setEmotion(targets[i % 3], 0.5, `step ${i}`);
        setEmotion('neutral', 0.3, `back ${i}`);
      }
      expect(emotionAtom.get().history.length).toBeLessThanOrEqual(20);
    });
  });

  describe('computed atoms', () => {
    it('emotionLabel returns current label', () => {
      setEmotion('curious', 0.6, 'test');
      setEmotion('creative', 0.7, 'test');
      expect(emotionLabel.get()).toBe('创造');
    });

    it('emotionEmoji returns current emoji', () => {
      setEmotion('curious', 0.7, 'test');
      setEmotion('focused', 0.8, 'test');
      setEmotion('frustrated', 0.7, 'test');
      expect(emotionEmoji.get()).toBe('😤');
    });
  });

  describe('suggestions', () => {
    it('addSuggestion creates suggestion with id and timestamp', () => {
      addSuggestion({ type: 'action', priority: 'high', emoji: '💡', title: 'Try this', description: 'A suggestion' });
      const items = suggestionsAtom.get();
      expect(items).toHaveLength(1);
      expect(items[0].id).toBeTruthy();
      expect(items[0].dismissed).toBe(false);
      expect(items[0].timestamp).toBeGreaterThan(0);
    });

    it('activeSuggestions filters dismissed', () => {
      addSuggestion({ type: 'action', priority: 'medium', emoji: '💡', title: 'A', description: 'a' });
      addSuggestion({ type: 'warning', priority: 'high', emoji: '⚠️', title: 'B', description: 'b' });
      expect(activeSuggestions.get()).toHaveLength(2);
      dismissSuggestion(suggestionsAtom.get()[0].id);
      expect(activeSuggestions.get()).toHaveLength(1);
    });

    it('dismissSuggestion marks specific suggestion', () => {
      addSuggestion({ type: 'action', priority: 'medium', emoji: '💡', title: 'A', description: 'a' });
      addSuggestion({ type: 'action', priority: 'medium', emoji: '💡', title: 'B', description: 'b' });
      const id = suggestionsAtom.get()[0].id;
      dismissSuggestion(id);
      expect(suggestionsAtom.get()[0].dismissed).toBe(true);
      expect(suggestionsAtom.get()[1].dismissed).toBe(false);
    });

    it('clearSuggestions removes all', () => {
      addSuggestion({ type: 'action', priority: 'medium', emoji: '💡', title: 'A', description: 'a' });
      clearSuggestions();
      expect(suggestionsAtom.get()).toHaveLength(0);
    });

    it('suggestion with resource request', () => {
      addSuggestion({ type: 'resource_request', priority: 'high', emoji: '📦', title: 'Need tokens', description: 'Requesting budget', resourceType: 'token_budget', resourceAmount: 1000 });
      const item = suggestionsAtom.get()[0];
      expect(item.resourceType).toBe('token_budget');
      expect(item.resourceAmount).toBe(1000);
    });
  });
});
