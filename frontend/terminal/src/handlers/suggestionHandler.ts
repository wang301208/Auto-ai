import { gatewayClient } from '../client/gateway';
import {
  addSuggestion,
  addNegotiation,
  checkShouldShow,
  showSuggestion,
  showNegotiation
} from '../stores';
import type { ProactiveSuggestion, ResourceNegotiation, InitiativeEvent } from '../types';
import { SuggestionType, SuggestionPriority } from '../types';

function convertInitiativeToSuggestion(event: InitiativeEvent): ProactiveSuggestion {
  const priority = event.urgency > 0.8 ? SuggestionPriority.HIGH : event.urgency > 0.5 ? SuggestionPriority.MEDIUM : SuggestionPriority.LOW;

  return {
    id: `initiative_${Date.now()}`,
    type: SuggestionType.ACTION_SUGGESTION,
    content: {
      zh: event.initiative.message,
      en: event.initiative.message
    },
    expectedEffect: {
      zh: `Desire: ${event.desire_type}, Urgency: ${event.urgency.toFixed(2)}`,
      en: `Desire: ${event.desire_type}, Urgency: ${event.urgency.toFixed(2)}`
    },
    options: [],
    priority,
    validUntil: new Date(Date.now() + 300000).toISOString(),
    createdAt: new Date().toISOString(),
    requiresApproval: event.initiative.requires_approval,
    metadata: {
      timestamp: event.initiative.timestamp,
      desire_type: event.desire_type,
      urgency: event.urgency
    }
  };
}

export async function registerSuggestionHandler() {
  try {
    const desireState = await gatewayClient.request<{ active_initiatives: InitiativeEvent[] }>('radical.desire_state');

    if (desireState.active_initiatives && desireState.active_initiatives.length > 0) {
      for (const initiativeEvent of desireState.active_initiatives) {
        try {
          const suggestion = convertInitiativeToSuggestion(initiativeEvent);
          if (checkShouldShow(suggestion)) {
            addSuggestion(suggestion);
            showSuggestion(suggestion);
          }
        } catch (error) {
          console.error('[SuggestionHandler] Failed to convert initiative:', error);
        }
      }
    }
  } catch (error) {
    console.error('[SuggestionHandler] Failed to fetch desire state:', error);
  }
}

export function registerNegotiationHandler() {
  return function() {};
}
