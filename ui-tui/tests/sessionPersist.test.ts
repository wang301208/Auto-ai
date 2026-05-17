import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { transcriptAtom, clearTranscript } from '../src/stores/transcriptStore.js';
import { sessionInfoAtom, statusAtom } from '../src/stores/sessionStore.js';
import { emotionAtom } from '../src/stores/emotionStore.js';
import { historyAtom } from '../src/stores/inputStore.js';
import { saveSession, loadSession, restoreSession, clearSession, startAutoSave, stopAutoSave } from '../src/stores/sessionPersist.js';

const SESSION_DIR = path.join(os.homedir(), '.autoai', 'sessions');
const SESSION_FILE = path.join(SESSION_DIR, 'current.json');

describe('sessionPersist', () => {
  beforeEach(() => {
    transcriptAtom.set([]);
    historyAtom.set([]);
    statusAtom.set('starting');
    emotionAtom.set({ current: 'neutral', intensity: 0.3, confidence: 0.5, reason: '系统启动', since: Date.now(), history: [] });
    try { fs.unlinkSync(SESSION_FILE); } catch {}
  });

  afterEach(() => {
    stopAutoSave();
    try { fs.unlinkSync(SESSION_FILE); } catch {}
  });

  describe('saveSession / loadSession', () => {
    it('saves and loads session data', () => {
      transcriptAtom.set([
        { id: '1', role: 'user', text: 'Hello', timestamp: Date.now() },
        { id: '2', role: 'assistant', text: 'Hi there', timestamp: Date.now() },
      ]);
      historyAtom.set(['Hello', '/help']);
      statusAtom.set('ready');

      saveSession();

      expect(fs.existsSync(SESSION_FILE)).toBe(true);
      const loaded = loadSession();
      expect(loaded).not.toBeNull();
      expect(loaded!.transcript).toHaveLength(2);
      expect(loaded!.transcript[0].text).toBe('Hello');
      expect(loaded!.inputHistory).toEqual(['Hello', '/help']);
      expect(loaded!.status).toBe('ready');
      expect(loaded!.version).toBe(1);
    });

    it('returns null when no session file exists', () => {
      expect(loadSession()).toBeNull();
    });

    it('returns null for expired sessions (>7 days)', () => {
      const expired = {
        version: 1,
        savedAt: Date.now() - 8 * 24 * 60 * 60 * 1000,
        transcript: [],
        sessionInfo: null,
        emotion: emotionAtom.get(),
        inputHistory: [],
        status: 'ready',
      };
      fs.mkdirSync(SESSION_DIR, { recursive: true });
      fs.writeFileSync(SESSION_FILE, JSON.stringify(expired), 'utf-8');
      expect(loadSession()).toBeNull();
    });

    it('returns null for wrong version', () => {
      const wrong = { version: 2, savedAt: Date.now(), transcript: [] };
      fs.mkdirSync(SESSION_DIR, { recursive: true });
      fs.writeFileSync(SESSION_FILE, JSON.stringify(wrong), 'utf-8');
      expect(loadSession()).toBeNull();
    });
  });

  describe('restoreSession', () => {
    it('restores transcript and history', () => {
      const data = {
        version: 1 as const,
        savedAt: Date.now(),
        transcript: [
          { id: '1', role: 'user' as const, text: 'test', timestamp: Date.now() },
        ],
        sessionInfo: { id: 'restored-session' },
        emotion: { current: 'curious' as const, intensity: 0.8, confidence: 0.7, reason: 'restored', since: Date.now(), history: [] },
        inputHistory: ['test', '/help'],
        status: 'ready',
      };

      restoreSession(data);

      expect(transcriptAtom.get()).toHaveLength(1);
      expect(transcriptAtom.get()[0].text).toBe('test');
      expect(historyAtom.get()).toEqual(['test', '/help']);
      expect(emotionAtom.get().current).toBe('curious');
      expect(statusAtom.get()).toBe('ready');
    });

    it('handles empty data gracefully', () => {
      const data = {
        version: 1 as const,
        savedAt: Date.now(),
        transcript: [],
        sessionInfo: null,
        emotion: emotionAtom.get(),
        inputHistory: [],
        status: 'starting',
      };

      restoreSession(data);
      expect(transcriptAtom.get()).toHaveLength(0);
    });
  });

  describe('clearSession', () => {
    it('removes session file', () => {
      saveSession();
      expect(fs.existsSync(SESSION_FILE)).toBe(true);
      clearSession();
      expect(fs.existsSync(SESSION_FILE)).toBe(false);
    });
  });

  describe('autoSave', () => {
    it('startAutoSave creates interval', () => {
      startAutoSave(100);
      transcriptAtom.set([{ id: '1', role: 'user' as const, text: 'auto', timestamp: Date.now() }]);
      setTimeout(() => {
        expect(fs.existsSync(SESSION_FILE)).toBe(true);
        stopAutoSave();
      }, 150);
    });
  });
});
