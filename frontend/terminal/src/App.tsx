import React, { useEffect } from 'react';
import { gatewayClient } from './client/gateway';
import { eventBus } from './client/eventBus';
import {
  registerPromptHandler,
  registerEmotionHandler,
  registerPersonaHandler,
  registerPersonaEvolutionHandler,
  registerSuggestionHandler,
  registerNegotiationHandler
} from './handlers';
import { Branding } from './components/Branding';
import { ContentRegion } from './components/ContentRegion';
import { InputRegion } from './components/InputRegion';
import { Overlays } from './components/Overlays';
import type { EmotionEvent as BackendEmotionEvent, InitiativeEvent } from './types/backend';
import type { EmotionEvent, ProactiveSuggestion } from './types';
import { SuggestionType, SuggestionPriority } from './types';

export function App() {
  useEffect(() => {
    async function init() {
      await gatewayClient.start();

      gatewayClient.on('event', (data: { type: string, payload: any }) => {
        if (data.type === 'avatar.update') {
          const emotion = data.payload as BackendEmotionEvent;
          eventBus.emit<EmotionEvent>('emotion.new', {
            type: emotion.type as EmotionEvent['type'],
            intensity: emotion.intensity,
            emoji: emotion.emoji || getEmotionEmoji(emotion.type),
            timestamp: emotion.timestamp,
            triggerReason: {
              zh: emotion.trigger_reason || '',
              en: emotion.trigger_reason || ''
            }
          });
        }
        if (data.type === 'radical.initiative') {
          const initiative = data.payload as InitiativeEvent;
          const priority = initiative.urgency > 0.8 ? SuggestionPriority.HIGH : initiative.urgency > 0.5 ? SuggestionPriority.MEDIUM : SuggestionPriority.LOW;
          const suggestion: ProactiveSuggestion = {
            id: `initiative_${Date.now()}`,
            type: SuggestionType.ACTION_SUGGESTION,
            content: {
              zh: initiative.initiative.message,
              en: initiative.initiative.message
            },
            expectedEffect: {
              zh: `Desire: ${initiative.desire_type}, Urgency: ${initiative.urgency.toFixed(2)}`,
              en: `Desire: ${initiative.desire_type}, Urgency: ${initiative.urgency.toFixed(2)}`
            },
            options: [],
            priority,
            validUntil: new Date(Date.now() + 300000).toISOString(),
            createdAt: new Date().toISOString(),
            requiresApproval: initiative.initiative.requires_approval,
            metadata: {
              timestamp: initiative.initiative.timestamp,
              desire_type: initiative.desire_type,
              urgency: initiative.urgency
            }
          };
          eventBus.emit('suggestion.new', suggestion);
        }
      });
    }

    init();
  }, []);

  useEffect(() => {
    const unsubscribers = [
      registerPromptHandler(),
      registerEmotionHandler(),
      registerPersonaHandler(),
      registerPersonaEvolutionHandler(),
      registerSuggestionHandler(),
      registerNegotiationHandler()
    ];

    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
      gatewayClient.stop();
    };
  }, []);

  return (
    <>
      <Branding />
      <ContentRegion />
      <InputRegion />
      <Overlays />
    </>
  );
}

function getEmotionEmoji(type: string): string {
  const emojiMap: Record<string, string> = {
    joy: '😊',
    anger: '😠',
    sadness: '😢',
    fear: '😨',
    surprise: '😲',
    disgust: '🤢',
    anticipation: '😏',
    trust: '🤝'
  };
  return emojiMap[type] || '😐';
}
