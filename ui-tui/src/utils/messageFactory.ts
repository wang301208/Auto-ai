import type { TranscriptMessage } from '../types.js';

let messageCounter = 0;
const pid = process.pid;

export function makeMessage(role: TranscriptMessage['role'], text: string): TranscriptMessage {
  return {
    id: `${Date.now()}:${++messageCounter}:${pid}`,
    role,
    text,
    timestamp: Date.now(),
  };
}

export function resetMessageCounter(): void {
  messageCounter = 0;
}
