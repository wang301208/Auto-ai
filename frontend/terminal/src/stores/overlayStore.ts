import { atom } from 'nanostores';
import type { ProactiveSuggestion, ResourceNegotiation } from '../types';

type OverlayType = 'suggestion' | 'negotiation' | null;

export const activeOverlay = atom<OverlayType>(null);
export const suggestionQueue = atom<ProactiveSuggestion[]>([]);
export const negotiationQueue = atom<ResourceNegotiation[]>([]);

export function showSuggestion(suggestion: ProactiveSuggestion) {
  activeOverlay.set('suggestion');
  suggestionQueue.set([suggestion]);
}

export function showNegotiation(negotiation: ResourceNegotiation) {
  activeOverlay.set('negotiation');
  negotiationQueue.set([negotiation]);
}

export function closeOverlay() {
  activeOverlay.set(null);
  suggestionQueue.set([]);
  negotiationQueue.set([]);
}
