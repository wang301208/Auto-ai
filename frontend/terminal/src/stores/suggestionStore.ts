import { atom, map } from 'nanostores';
import type {
  ProactiveSuggestion,
  ResourceNegotiation,
  SuggestionAction,
  SuggestionResponse
} from '../types';

export const activeSuggestions = atom<ProactiveSuggestion[]>([]);
export const pendingNegotiations = atom<ResourceNegotiation[]>([]);
export const rejectedSuggestions = map<Set<string>>(new Set());
export const userPreferences = map<Map<string, { rejected: number; lastRejected: string }>>(new Map());

export function addSuggestion(suggestion: ProactiveSuggestion) {
  const suggestions = activeSuggestions.get();
  activeSuggestions.set([...suggestions, suggestion]);
}

export function respondSuggestion(suggestionId: string, action: SuggestionAction, negotiatedContent?: string): SuggestionResponse {
  const suggestions = activeSuggestions.get();
  const index = suggestions.findIndex(s => s.id === suggestionId);
  
  if (index === -1) {
    throw new Error(`Suggestion ${suggestionId} not found`);
  }
  
  const suggestion = suggestions[index];
  activeSuggestions.set(suggestions.filter(s => s.id !== suggestionId));
  
  const response: SuggestionResponse = {
    suggestionId,
    action,
    negotiatedContent,
    timestamp: new Date().toISOString()
  };
  
  if (action === 'reject') {
    const rejected = rejectedSuggestions.get();
    const newRejected = new Set(rejected);
    newRejected.add(suggestionId);
    rejectedSuggestions.set(newRejected);
    
    const prefs = userPreferences.get();
    const newPrefs = new Map(prefs);
    const existing = newPrefs.get(suggestion.type) || { rejected: 0, lastRejected: '' };
    newPrefs.set(suggestion.type, {
      rejected: existing.rejected + 1,
      lastRejected: new Date().toISOString()
    });
    userPreferences.set(newPrefs);
  }
  
  return response;
}

export function addNegotiation(negotiation: ResourceNegotiation) {
  const negotiations = pendingNegotiations.get();
  pendingNegotiations.set([...negotiations, negotiation]);
}

export function respondNegotiation(
  negotiationId: string,
  userAction: SuggestionAction,
  negotiatedContent?: string
) {
  const negotiations = pendingNegotiations.get();
  const index = negotiations.findIndex(n => n.id === negotiationId);
  
  if (index === -1) {
    throw new Error(`Negotiation ${negotiationId} not found`);
  }
  
  const negotiation = negotiations[index];
  pendingNegotiations.set(negotiations.filter(n => n.id !== negotiationId));
  
  return {
    negotiationId,
    userAction,
    negotiatedContent,
    timestamp: new Date().toISOString()
  };
}

export function checkShouldShow(suggestion: ProactiveSuggestion): boolean {
  const rejected = rejectedSuggestions.get();
  if (rejected.has(suggestion.id)) {
    return false;
  }
  
  const prefs = userPreferences.get();
  const pref = prefs.get(suggestion.type);
  if (pref && pref.rejected > 5) {
    const lastRejected = new Date(pref.lastRejected);
    const cooldown = 30 * 60 * 1000; // 30 minutes
    if (Date.now() - lastRejected.getTime() < cooldown) {
      return false;
    }
  }
  
  return true;
}
