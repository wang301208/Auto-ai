import { eventBus } from '../client/eventBus';
import { updatePersona, addEvolutionRecord } from '../stores/personaStore';
import type { PersonaState, PersonaEvolutionRecord } from '../types';

export function registerPersonaHandler() {
  const unsubscribe = eventBus.on<PersonaState>('persona.update', (data) => {
    try {
      updatePersona(data);
    } catch (error) {
      console.error('[PersonaHandler] Failed to update persona state:', error);
    }
  });

  return unsubscribe;
}

export function registerPersonaEvolutionHandler() {
  const unsubscribe = eventBus.on<PersonaEvolutionRecord>('persona.evolution', (record) => {
    try {
      addEvolutionRecord(record);
    } catch (error) {
      console.error('[PersonaHandler] Failed to add evolution record:', error);
    }
  });

  return unsubscribe;
}
