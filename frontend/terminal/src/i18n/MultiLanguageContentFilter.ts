import type { BilingualText, LanguageMode, BilingualContentFilterResult } from '../types';

export class MultiLanguageContentFilter {
  filterContent(
    content: BilingualText,
    languageMode: LanguageMode
  ): BilingualContentFilterResult {
    if (languageMode === 'zh') {
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

  filterContentSafe(content: BilingualText): BilingualContentFilterResult {
    const mode = 'zh' as LanguageMode;
    return this.filterContent(content, mode);
  }
}

export const multiLanguageContentFilter = new MultiLanguageContentFilter();
