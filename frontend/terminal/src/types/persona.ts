import type { BilingualText } from './bilingual';

export interface PersonaFeatures {
  languageFormality: number;
  responseDetailLevel: number;
  suggestionProactiveness: number;
  humorLevel: number;
  empathyLevel: number;
  technicalDepth: number;
}

export interface PersonaState {
  userId: string;
  features: PersonaFeatures;
  evolutionVersion: number;
  lastUpdated: string;
  evolutionHistory: PersonaEvolutionRecord[];
  isManualMode: boolean;
}

export interface PersonaEvolutionRecord {
  version: number;
  timestamp: string;
  trigger: 'auto' | 'manual';
  changes: Partial<PersonaFeatures>;
  reason: BilingualText;
}

export enum InteractionEventType {
  PROMPT = 'prompt',
  RESPONSE = 'response',
  SUGGESTION_ACCEPT = 'suggestion_accept',
  SUGGESTION_REJECT = 'suggestion_reject',
  CLARIFICATION = 'clarification'
}

export enum LanguageStyle {
  FORMAL = 'formal',
  CASUAL = 'casual'
}

export interface InteractionEvent {
  userId: string;
  sessionId: string;
  eventType: InteractionEventType;
  contentLength: number;
  languageStyle: LanguageStyle;
  responseTime: number;
  timestamp: string;
}

export interface InteractionPattern {
  preferredLanguageStyle: LanguageStyle;
  averageResponseDetailPreference: number;
  suggestionAcceptanceRate: number;
  preferredResponseSpeed: 'fast' | 'moderate' | 'slow';
  technicalInterestLevel: number;
}

export interface PersonalizedResponse {
  content: BilingualText;
  style: {
    formalityLevel: number;
    detailLevel: number;
    tone: 'neutral' | 'warm' | 'professional' | 'friendly';
  };
  suggestions?: string[];
}
