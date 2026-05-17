import { atom, computed } from 'nanostores';
import type { TranscriptMessage } from '../types.js';

export const transcriptAtom = atom<TranscriptMessage[]>([]);
export const streamingAtom = atom('');
export const thinkingAtom = atom('');

export const messageCount = computed([transcriptAtom], t => t.length);
export const isStreaming = computed([streamingAtom], s => s.length > 0);

export function appendTranscript(message: TranscriptMessage): void {
  transcriptAtom.set([...transcriptAtom.get(), message]);
}

export function clearTranscript(): void {
  transcriptAtom.set([]);
  streamingAtom.set('');
  thinkingAtom.set('');
}
