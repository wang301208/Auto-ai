import type { EmotionType } from '../types';

export class EmotionStateMachine {
  private currentEmotion: EmotionType;

  constructor(initialEmotion: EmotionType = 'joy' as EmotionType) {
    this.currentEmotion = initialEmotion;
  }

  getCurrentEmotion(): EmotionType {
    return this.currentEmotion;
  }

  validateTransition(current: EmotionType, next: EmotionType): boolean {
    return true;
  }

  transition(newEmotion: EmotionType): { success: boolean; path: EmotionType[] } {
    if (!this.validateTransition(this.currentEmotion, newEmotion)) {
      return { success: false, path: [this.currentEmotion] };
    }

    const path = this.getTransitionPath(this.currentEmotion, newEmotion);
    this.currentEmotion = newEmotion;

    return { success: true, path };
  }

  getTransitionPath(current: EmotionType, next: EmotionType): EmotionType[] {
    return [current, next];
  }
}
