import type {
  BilingualText,
  PersonalizedResponse,
  PersonaFeatures,
  EmotionType
} from '../types';

export class PersonalizedResponseGenerator {
  generate(
    baseContent: BilingualText,
    persona: PersonaFeatures,
    emotion: EmotionType
  ): PersonalizedResponse {
    const adjustedContent = this.adjustContent(baseContent, persona);

    return {
      content: adjustedContent,
      style: {
        formalityLevel: persona.languageFormality,
        detailLevel: persona.responseDetailLevel,
        tone: this.determineTone(emotion, persona)
      },
      suggestions: this.generateSuggestions(persona)
    };
  }

  private adjustContent(content: BilingualText, persona: PersonaFeatures): BilingualText {
    return content;
  }

  private determineTone(
    emotion: EmotionType,
    persona: PersonaFeatures
  ): 'neutral' | 'warm' | 'professional' | 'friendly' {
    if (persona.languageFormality > 0.7) {
      return 'professional';
    }

    if (persona.empathyLevel > 0.6) {
      return 'warm';
    }

    if (persona.humorLevel > 0.6) {
      return 'friendly';
    }

    return 'neutral';
  }

  private generateSuggestions(persona: PersonaFeatures): string[] {
    if (persona.suggestionProactiveness < 0.3) {
      return [];
    }

    return [
      '是否需要进一步的帮助? / Would you like further assistance?',
      '可以尝试相关功能。 / You can try related features.'
    ];
  }
}

export const personalizedResponseGenerator = new PersonalizedResponseGenerator();
