import { eventBus } from '../client/eventBus';
import { updateEmotion } from '../stores/emotionStore';
import type { EmotionEvent } from '../types';
import { EmotionType } from '../types';

export function registerEmotionHandler() {
  const unsubscribe = eventBus.on<EmotionEvent>('emotion.new', (event) => {
    try {
      updateEmotion(event);
    } catch (error) {
      console.error('[EmotionHandler] Failed to update emotion:', error);
    }
  });

  return unsubscribe;
}
