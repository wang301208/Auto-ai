import type { EmotionTheme, EmotionType } from '../types';
import { AnimationType } from '../types';

const JOY: EmotionTheme = {
  primaryColor: '#FFD700',
  secondaryColor: '#FFA500',
  backgroundColor: '#FFF8DC',
  textColor: '#2C3E50',
  accentColor: '#FF6347',
  animationType: AnimationType.PULSE
};

const ANGER: EmotionTheme = {
  primaryColor: '#FF4444',
  secondaryColor: '#CC0000',
  backgroundColor: '#FFE6E6',
  textColor: '#2C3E50',
  accentColor: '#8B0000',
  animationType: AnimationType.SHAKE
};

const SADNESS: EmotionTheme = {
  primaryColor: '#4682B4',
  secondaryColor: '#5F9EA0',
  backgroundColor: '#E6F3FF',
  textColor: '#2C3E50',
  accentColor: '#4169E1',
  animationType: AnimationType.SLIDE
};

const FEAR: EmotionTheme = {
  primaryColor: '#9370DB',
  secondaryColor: '#8A2BE2',
  backgroundColor: '#F3E5F5',
  textColor: '#2C3E50',
  accentColor: '#6A0DAD',
  animationType: AnimationType.GLOW
};

const SURPRISE: EmotionTheme = {
  primaryColor: '#FF1493',
  secondaryColor: '#FF69B4',
  backgroundColor: '#FFE4E1',
  textColor: '#2C3E50',
  accentColor: '#C71585',
  animationType: AnimationType.PULSE
};

const DISGUST: EmotionTheme = {
  primaryColor: '#556B2F',
  secondaryColor: '#6B8E23',
  backgroundColor: '#F5F5DC',
  textColor: '#2C3E50',
  accentColor: '#2F4F4F',
  animationType: AnimationType.SHAKE
};

const ANTICIPATION: EmotionTheme = {
  primaryColor: '#20B2AA',
  secondaryColor: '#48D1CC',
  backgroundColor: '#E0FFFF',
  textColor: '#2C3E50',
  accentColor: '#00CED1',
  animationType: AnimationType.GLOW
};

const TRUST: EmotionTheme = {
  primaryColor: '#32CD32',
  secondaryColor: '#3CB371',
  backgroundColor: '#F0FFF0',
  textColor: '#2C3E50',
  accentColor: '#228B22',
  animationType: AnimationType.PULSE
};

const emotionThemes: Record<EmotionType, EmotionTheme> = {
  joy: JOY,
  anger: ANGER,
  sadness: SADNESS,
  fear: FEAR,
  surprise: SURPRISE,
  disgust: DISGUST,
  anticipation: ANTICIPATION,
  trust: TRUST
};

export class EmotionThemeManager {
  getTheme(emotionType: EmotionType): EmotionTheme {
    return emotionThemes[emotionType];
  }

  applyTheme(theme: EmotionTheme): void {
    console.log(`[EmotionThemeManager] Applied theme:`, theme);
  }
}

export const emotionThemeManager = new EmotionThemeManager();
