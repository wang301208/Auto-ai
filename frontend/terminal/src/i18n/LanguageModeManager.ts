import type { LanguageMode } from '../types';

export class LanguageModeManager {
  private currentMode: LanguageMode = 'zh' as LanguageMode;
  private listeners: Set<(mode: LanguageMode) => void> = new Set();

  switchLanguage(newMode: LanguageMode): void {
    if (this.currentMode === newMode) {
      return;
    }

    const previousMode = this.currentMode;
    this.currentMode = newMode;

    this.notifyListeners(newMode);
  }

  onLanguageChange(callback: (mode: LanguageMode) => void): () => void {
    this.listeners.add(callback);

    return () => {
      this.listeners.delete(callback);
    };
  }

  getCurrentMode(): LanguageMode {
    return this.currentMode;
  }

  private notifyListeners(mode: LanguageMode): void {
    this.listeners.forEach(callback => {
      try {
        callback(mode);
      } catch (error) {
        console.error('[LanguageModeManager] Error in listener:', error);
      }
    });
  }
}

export const languageModeManager = new LanguageModeManager();
