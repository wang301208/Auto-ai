import type { ProactiveSuggestion, SuggestionResponse, SuggestionType } from '../types';

export class PreferenceLearner {
  private preferences: Map<SuggestionType, { rejected: number; lastRejected: string }> = new Map();
  private rejectionThreshold: number = 5;
  private cooldownPeriod: number = 30 * 60 * 1000; // 30 minutes

  learnFromResponse(suggestion: ProactiveSuggestion, response: SuggestionResponse): void {
    if (response.action === 'reject') {
      const existing = this.preferences.get(suggestion.type) || { rejected: 0, lastRejected: '' };
      this.preferences.set(suggestion.type, {
        rejected: existing.rejected + 1,
        lastRejected: new Date().toISOString()
      });
    } else if (response.action === 'confirm') {
      const existing = this.preferences.get(suggestion.type) || { rejected: 0, lastRejected: '' };
      this.preferences.set(suggestion.type, {
        rejected: Math.max(0, existing.rejected - 1),
        lastRejected: existing.lastRejected
      });
    }
  }

  updatePreferences(): void {
    console.log('[PreferenceLearner] Preferences updated');
  }

  getSuggestionFilter(): (suggestion: ProactiveSuggestion) => boolean {
    return (suggestion: ProactiveSuggestion) => {
      const pref = this.preferences.get(suggestion.type);

      if (!pref || pref.rejected < this.rejectionThreshold) {
        return true;
      }

      const lastRejected = new Date(pref.lastRejected);
      const elapsed = Date.now() - lastRejected.getTime();

      return elapsed > this.cooldownPeriod;
    };
  }
}

export const preferenceLearner = new PreferenceLearner();
