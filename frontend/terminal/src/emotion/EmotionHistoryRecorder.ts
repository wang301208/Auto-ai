import type { EmotionType, BilingualText } from '../types';

interface EmotionHistoryItem {
  type: EmotionType;
  previousType: EmotionType;
  triggerReason: BilingualText;
  timestamp: string;
}

export class EmotionHistoryRecorder {
  private history: EmotionHistoryItem[] = [];
  private maxHistory: number = 100;

  record(
    emotion: EmotionType,
    previousEmotion: EmotionType,
    trigger: BilingualText
  ): void {
    const item: EmotionHistoryItem = {
      type: emotion,
      previousType: previousEmotion,
      triggerReason: trigger,
      timestamp: new Date().toISOString()
    };

    this.history.push(item);

    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }
  }

  getHistory(limit?: number): EmotionHistoryItem[] {
    if (limit) {
      return this.history.slice(-limit);
    }
    return [...this.history];
  }

  clearHistory(): void {
    this.history = [];
  }
}

export const emotionHistoryRecorder = new EmotionHistoryRecorder();
