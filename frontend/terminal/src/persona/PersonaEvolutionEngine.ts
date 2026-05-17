import type {
  PersonaFeatures,
  PersonaState,
  PersonaEvolutionRecord,
  InteractionPattern,
  BilingualText
} from '../types';

export class PersonaEvolutionEngine {
  evolve(
    currentPersona: PersonaState,
    pattern: InteractionPattern
  ): PersonaEvolutionRecord {
    const changes: Partial<PersonaFeatures> = {};

    changes.languageFormality = this.adjustLanguageFormality(
      currentPersona.features.languageFormality,
      pattern.preferredLanguageStyle
    );

    changes.responseDetailLevel = this.adjustResponseDetailLevel(
      currentPersona.features.responseDetailLevel,
      pattern.averageResponseDetailPreference
    );

    changes.suggestionProactiveness = this.adjustSuggestionProactiveness(
      currentPersona.features.suggestionProactiveness,
      pattern.suggestionAcceptanceRate
    );

    changes.technicalDepth = this.adjustTechnicalDepth(
      currentPersona.features.technicalDepth,
      pattern.technicalInterestLevel
    );

    return {
      version: currentPersona.evolutionVersion + 1,
      timestamp: new Date().toISOString(),
      trigger: 'auto',
      changes,
      reason: {
        zh: '基于交互历史的自动演化',
        en: 'Automatic evolution based on interaction history'
      }
    };
  }

  private adjustLanguageFormality(
    current: number,
    preferredStyle: 'formal' | 'casual'
  ): number {
    const target = preferredStyle === 'formal' ? 0.8 : 0.2;
    return this.moveTowards(current, target, 0.1);
  }

  private adjustResponseDetailLevel(
    current: number,
    preference: number
  ): number {
    return this.moveTowards(current, preference, 0.1);
  }

  private adjustSuggestionProactiveness(
    current: number,
    acceptanceRate: number
  ): number {
    const target = acceptanceRate > 0.6 ? 0.8 : 0.3;
    return this.moveTowards(current, target, 0.1);
  }

  private adjustTechnicalDepth(
    current: number,
    interestLevel: number
  ): number {
    return this.moveTowards(current, interestLevel, 0.1);
  }

  private moveTowards(current: number, target: number, step: number): number {
    if (Math.abs(current - target) < step) {
      return target;
    }
    return current < target ? current + step : current - step;
  }
}

export const personaEvolutionEngine = new PersonaEvolutionEngine();
