import { atom } from 'nanostores';
import type { SessionInfo, Usage } from '../types.js';

export type SessionStatus =
  | 'starting'
  | 'ready'
  | 'running'
  | 'streaming'
  | 'queued'
  | 'error'
  | 'interrupted'
  | 'gateway log'
  | 'context compacted'
  | 'parallel agents'
  | 'parallel complete'
  | 'parallel errors'
  | 'gateway exited'
  | 'gateway reloading'
  | 'disconnected'
  | 'autonomous'
  | string;

export const sessionInfoAtom = atom<SessionInfo | null>(null);
export const usageAtom = atom<Usage | undefined>(undefined);
export const busyAtom = atom(false);
export const statusAtom = atom<SessionStatus>('starting');
