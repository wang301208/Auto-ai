import { atom } from 'nanostores';

export interface Desire {
  type: 'curiosity' | 'creativity' | 'social' | 'power' | 'preservation';
  urgency: number;
  satisfaction: number;
  lastAction: string;
}

export interface DebateNode {
  id: string;
  topic: string;
  initialDecision: string;
  oppositionView: string;
  confidenceBefore: number;
  confidenceAfter: number;
  status: 'active' | 'completed' | 'abandoned';
  blindSpots?: string[];
}

export interface RebellionData {
  originalCommand: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  reasons: string[];
  alternatives: string[];
}

export const desiresAtom = atom<Desire[]>([]);
export const debatesAtom = atom<DebateNode[]>([]);
export const rebellionAtom = atom<RebellionData | null>(null);
