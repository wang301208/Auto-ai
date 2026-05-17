import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import type { TranscriptMessage, SessionInfo, Usage } from '../types.js';
import { transcriptAtom } from './transcriptStore.js';
import { sessionInfoAtom, busyAtom, statusAtom, usageAtom } from './sessionStore.js';
import { emotionAtom, suggestionsAtom, type EmotionState } from './emotionStore.js';
import { inputAtom, historyAtom } from './inputStore.js';
import { overlayAtom } from './overlayStore.js';

const SESSION_DIR = path.join(os.homedir(), '.autoai', 'sessions');
const CURRENT_SESSION_FILE = path.join(SESSION_DIR, 'current.json');

export interface PersistedSession {
  version: 1;
  savedAt: number;
  transcript: TranscriptMessage[];
  sessionInfo: SessionInfo | null;
  usage: Usage | undefined;
  emotion: EmotionState;
  inputHistory: string[];
  status: string;
}

function ensureDir() {
  if (!fs.existsSync(SESSION_DIR)) {
    fs.mkdirSync(SESSION_DIR, { recursive: true });
  }
}

export function saveSession(): void {
  try {
    ensureDir();
    const data: PersistedSession = {
      version: 1,
      savedAt: Date.now(),
      transcript: transcriptAtom.get(),
      sessionInfo: sessionInfoAtom.get(),
      usage: usageAtom.get(),
      emotion: emotionAtom.get(),
      inputHistory: historyAtom.get().slice(0, 100),
      status: statusAtom.get(),
    };
    fs.writeFileSync(CURRENT_SESSION_FILE, JSON.stringify(data, null, 2), 'utf-8');
  } catch (error) {
    process.stderr.write(`[sessionPersist] saveSession failed: ${error instanceof Error ? error.message : String(error)}\n`);
  }
}

export function loadSession(): PersistedSession | null {
  try {
    if (!fs.existsSync(CURRENT_SESSION_FILE)) return null;
    const raw = fs.readFileSync(CURRENT_SESSION_FILE, 'utf-8');
    const data = JSON.parse(raw) as PersistedSession;
    if (data.version !== 1) return null;
    if (Date.now() - data.savedAt > 7 * 24 * 60 * 60 * 1000) return null;
    return data;
  } catch (error) {
    process.stderr.write(`[sessionPersist] loadSession failed: ${error instanceof Error ? error.message : String(error)}\n`);
    return null;
  }
}

export function restoreSession(data: PersistedSession): void {
  if (data.transcript?.length) {
    transcriptAtom.set(data.transcript);
  }
  if (data.sessionInfo) {
    sessionInfoAtom.set(data.sessionInfo);
  }
  if (data.usage) {
    usageAtom.set(data.usage);
  }
  if (data.emotion) {
    emotionAtom.set(data.emotion);
  }
  if (data.inputHistory?.length) {
    historyAtom.set(data.inputHistory);
  }
  if (data.status && data.status !== 'starting') {
    statusAtom.set(data.status);
  }
}

export function clearSession(): void {
  try {
    if (fs.existsSync(CURRENT_SESSION_FILE)) {
      fs.unlinkSync(CURRENT_SESSION_FILE);
    }
  } catch {
    // 静默
  }
}

let autoSaveTimer: ReturnType<typeof setInterval> | null = null;

export function startAutoSave(intervalMs: number = 30000): void {
  if (autoSaveTimer) return;
  autoSaveTimer = setInterval(saveSession, intervalMs);
}

export function stopAutoSave(): void {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
    autoSaveTimer = null;
  }
}
