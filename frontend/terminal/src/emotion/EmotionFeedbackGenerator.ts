import type { EmotionType, EmotionFeedback } from '../types';

export class EmotionFeedbackGenerator {
  generate(emotion: EmotionType): EmotionFeedback {
    const feedbackMap: Record<EmotionType, EmotionFeedback> = {
      joy: {
        greetingStyle: 'enthusiastic',
        responseTone: 'warm',
        suggestionStyle: 'direct'
      },
      anger: {
        greetingStyle: 'reserved',
        responseTone: 'urgent',
        suggestionStyle: 'assertive'
      },
      sadness: {
        greetingStyle: 'casual',
        responseTone: 'calm',
        suggestionStyle: 'hesitant'
      },
      fear: {
        greetingStyle: 'casual',
        responseTone: 'urgent',
        suggestionStyle: 'hesitant'
      },
      surprise: {
        greetingStyle: 'enthusiastic',
        responseTone: 'warm',
        suggestionStyle: 'gentle'
      },
      disgust: {
        greetingStyle: 'reserved',
        responseTone: 'neutral',
        suggestionStyle: 'hesitant'
      },
      anticipation: {
        greetingStyle: 'enthusiastic',
        responseTone: 'warm',
        suggestionStyle: 'direct'
      },
      trust: {
        greetingStyle: 'casual',
        responseTone: 'warm',
        suggestionStyle: 'gentle'
      }
    };

    return feedbackMap[emotion] || {
      greetingStyle: 'formal',
      responseTone: 'neutral',
      suggestionStyle: 'direct'
    };
  }
}

export const emotionFeedbackGenerator = new EmotionFeedbackGenerator();
