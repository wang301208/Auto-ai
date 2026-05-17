import type { BilingualText } from './bilingual';

export enum EmotionType {
  JOY = 'joy',
  ANGER = 'anger',
  SADNESS = 'sadness',
  FEAR = 'fear',
  SURPRISE = 'surprise',
  DISGUST = 'disgust',
  ANTICIPATION = 'anticipation',
  TRUST = 'trust'
}

export enum AnimationType {
  PULSE = 'pulse',
  SHAKE = 'shake',
  GLOW = 'glow',
  SLIDE = 'slide'
}

export interface EmotionTheme {
  primaryColor: string;
  secondaryColor: string;
  backgroundColor: string;
  textColor: string;
  accentColor: string;
  animationType: AnimationType;
}

export interface EmotionState {
  type: EmotionType;
  intensity: number;
  triggerReason: BilingualText;
  timestamp: string;
  emoji: string;
}

export interface EmotionFeedback {
  greetingStyle: 'formal' | 'casual' | 'enthusiastic' | 'reserved';
  responseTone: 'neutral' | 'warm' | 'urgent' | 'calm';
  suggestionStyle: 'direct' | 'gentle' | 'assertive' | 'hesitant';
}

export interface EmotionHistoryRecord {
  type: EmotionType;
  previousType: EmotionType;
  triggerReason: BilingualText;
  timestamp: string;
}

export interface EmotionHistoryResponse {
  sessionId: string;
  records: EmotionHistoryRecord[];
  total: number;
}
