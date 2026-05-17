import { atom, map } from 'nanostores';
import type {
  BilingualText,
  BilingualContentFilterResult
} from '../types';
import { LanguageMode } from '../types';

export const currentMode = atom<LanguageMode>(LanguageMode.ZH);
export const fallbackLanguage = atom<'zh'>('zh');
export const supportedLanguages = atom<('zh' | 'en')[]>(['zh', 'en']);

export function switchLanguage(newMode: LanguageMode) {
  currentMode.set(newMode);
}

export function filterContent(content: BilingualText, languageMode: LanguageMode): BilingualContentFilterResult {
  if (languageMode === LanguageMode.ZH) {
    return {
      text: content.zh,
      hasFallback: false
    };
  }
  
  if (content.en) {
    return {
      text: content.en,
      hasFallback: false
    };
  }
  
  return {
    text: content.zh,
    hasFallback: true
  };
}

export function filterContentSafe(content: BilingualText): BilingualContentFilterResult {
  const mode = currentMode.get();
  return filterContent(content, mode);
}
