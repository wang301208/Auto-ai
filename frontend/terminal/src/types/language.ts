export enum LanguageMode {
  ZH = 'zh',
  BILINGUAL = 'bilingual'
}

export interface LanguageState {
  currentMode: LanguageMode;
  fallbackLanguage: 'zh';
  supportedLanguages: ('zh' | 'en')[];
}

export interface LanguageSwitchResponse {
  currentMode: LanguageMode;
  previousMode: LanguageMode;
  timestamp: string;
}

export interface BilingualContentFilterResult {
  text: string;
  hasFallback: boolean;
}
