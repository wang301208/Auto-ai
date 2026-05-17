import type {
  ProactiveSuggestion,
  SuggestionResponse,
  SuggestionAction
} from '../types';

export class SuggestionManager {
  private suggestions: Map<string, ProactiveSuggestion> = new Map();

  addSuggestion(suggestion: ProactiveSuggestion): void {
    this.suggestions.set(suggestion.id, suggestion);
  }

  shouldShowSuggestion(suggestion: ProactiveSuggestion): boolean {
    const now = Date.now();
    const expiry = new Date(suggestion.validUntil).getTime();

    if (now > expiry) {
      return false;
    }

    return true;
  }

  handleResponse(suggestionId: string, action: SuggestionAction): SuggestionResponse {
    const suggestion = this.suggestions.get(suggestionId);

    if (!suggestion) {
      throw new Error(`Suggestion ${suggestionId} not found`);
    }

    this.suggestions.delete(suggestionId);

    return {
      suggestionId,
      action,
      timestamp: new Date().toISOString()
    };
  }

  getSuggestion(suggestionId: string): ProactiveSuggestion | undefined {
    return this.suggestions.get(suggestionId);
  }

  getAllSuggestions(): ProactiveSuggestion[] {
    return Array.from(this.suggestions.values());
  }
}

export const suggestionManager = new SuggestionManager();
