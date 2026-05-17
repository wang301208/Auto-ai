import type {
  ProactiveInteractionRecord,
  SuggestionResponse,
  NegotiationResult,
  ProactiveSuggestion,
  ResourceNegotiation
} from '../types';
import { SuggestionAction } from '../types';

export class InteractionHistoryTracker {
  private history: ProactiveInteractionRecord[] = [];
  private maxHistory: number = 100;

  trackSuggestion(suggestion: ProactiveSuggestion, response: SuggestionResponse): void {
    const record: ProactiveInteractionRecord = {
      type: 'suggestion' as const,
      id: suggestion.id,
      content: suggestion.content,
      userAction: response.action,
      timestamp: response.timestamp
    };

    this.addRecord(record);
  }

  trackNegotiation(negotiation: ResourceNegotiation, result: NegotiationResult): void {
    let userAction: SuggestionAction;
    if (result.status === 'accepted') {
      userAction = SuggestionAction.CONFIRM;
    } else if (result.status === 'rejected') {
      userAction = SuggestionAction.REJECT;
    } else {
      userAction = SuggestionAction.NEGOTIATE;
    }
    
    const record: ProactiveInteractionRecord = {
      type: 'negotiation' as const,
      id: negotiation.id,
      resourceType: negotiation.resourceType,
      requestedAmount: negotiation.requestedAmount,
      userAction: userAction,
      finalAmount: result.allocatedResources,
      timestamp: new Date().toISOString()
    };

    this.addRecord(record);
  }

  getHistory(sessionId?: string): ProactiveInteractionRecord[] {
    if (sessionId) {
      return this.history.filter(record => record.type === 'suggestion');
    }
    return [...this.history];
  }

  private addRecord(record: ProactiveInteractionRecord): void {
    this.history.push(record);

    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }
  }
}

export const interactionHistoryTracker = new InteractionHistoryTracker();
