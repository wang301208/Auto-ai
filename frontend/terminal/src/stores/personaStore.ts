import { atom, map } from 'nanostores';
import type {
  PersonaState,
  PersonaFeatures,
  PersonaEvolutionRecord
} from '../types';

const DEFAULT_PERSONA_FEATURES: PersonaFeatures = {
  languageFormality: 0.5,
  responseDetailLevel: 0.5,
  suggestionProactiveness: 0.5,
  humorLevel: 0.3,
  empathyLevel: 0.5,
  technicalDepth: 0.5
};

export const currentState = atom<PersonaState>({
  userId: '',
  features: DEFAULT_PERSONA_FEATURES,
  evolutionVersion: 0,
  lastUpdated: new Date().toISOString(),
  evolutionHistory: [],
  isManualMode: false
});

export function updatePersona(state: PersonaState) {
  currentState.set(state);
}

export function adjustFeatures(newFeatures: Partial<PersonaFeatures>) {
  const state = currentState.get();
  const updatedFeatures = {
    ...state.features,
    ...newFeatures
  };
  
  const changes: Partial<PersonaFeatures> = {};
  for (const key in newFeatures) {
    if (state.features[key as keyof PersonaFeatures] !== updatedFeatures[key as keyof PersonaFeatures]) {
      changes[key as keyof PersonaFeatures] = updatedFeatures[key as keyof PersonaFeatures];
    }
  }
  
  const evolutionRecord: PersonaEvolutionRecord = {
    version: state.evolutionVersion + 1,
    timestamp: new Date().toISOString(),
    trigger: 'manual',
    changes,
    reason: {
      zh: '用户手动调整',
      en: 'Manual adjustment by user'
    }
  };
  
  currentState.set({
    ...state,
    features: updatedFeatures,
    evolutionVersion: state.evolutionVersion + 1,
    lastUpdated: new Date().toISOString(),
    evolutionHistory: [...state.evolutionHistory, evolutionRecord],
    isManualMode: true
  });
}

export function addEvolutionRecord(record: PersonaEvolutionRecord) {
  const state = currentState.get();
  const updatedFeatures = {
    ...state.features,
    ...record.changes
  };
  
  currentState.set({
    ...state,
    features: updatedFeatures,
    evolutionVersion: record.version,
    lastUpdated: record.timestamp,
    evolutionHistory: [...state.evolutionHistory, record]
  });
}

export function setManualMode(isManual: boolean) {
  const state = currentState.get();
  currentState.set({
    ...state,
    isManualMode: isManual
  });
}
