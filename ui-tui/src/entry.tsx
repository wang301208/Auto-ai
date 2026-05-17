import React from 'react';
import { render } from 'ink';
import App from './app.js';
import ErrorBoundary from './components/errorBoundary.js';
import { GatewayClient } from './gatewayClient.js';
import { loadSession, restoreSession, saveSession, startAutoSave, stopAutoSave } from './stores/sessionPersist.js';
import { TIMEOUTS } from './constants.js';
import {
  enterAlternateScreen,
  exitAlternateScreen,
  enableAlternateScroll,
  disableAlternateScroll,
} from './terminal/index.js';

function logError(context: string, error: unknown): void {
  const msg = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : '';
  process.stderr.write(`\n[FATAL ${context}] ${msg}\n${stack || ''}\n`);
}

async function main() {
  if (!process.stdin.isTTY) {
    console.error('Error: TUI requires an interactive TTY');
    process.exit(1);
  }

  const gateway = new GatewayClient();
  let cleanedUp = false;
  let instance: ReturnType<typeof render> | null = null;

  const cleanup = (reason: string = 'unknown') => {
    if (cleanedUp) return;
    cleanedUp = true;

    process.stderr.write(`\n[CLEANUP] Reason: ${reason}\n`);

    stopAutoSave();
    try {
      saveSession();
      process.stderr.write('[CLEANUP] Session saved\n');
    } catch (e) {
      logError('saveSession', e);
    }

    if (instance) {
      try {
        instance.unmount();
      } catch {}
    }

    try {
      gateway.stop();
    } catch {}

    disableAlternateScroll();
    exitAlternateScreen();
  };

  process.on('SIGINT', () => {
    cleanup('SIGINT');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    cleanup('SIGTERM');
    process.exit(0);
  });

  process.on('uncaughtException', (error) => {
    logError('uncaughtException', error);
    cleanup('uncaughtException');
    process.exit(1);
  });

  process.on('unhandledRejection', (reason) => {
    logError('unhandledRejection', reason);
  });

  process.on('exit', () => {
    if (!cleanedUp) {
      try {
        saveSession();
      } catch {}
    }
  });

  try {
    const startPromise = gateway.start();
    const timeoutPromise = new Promise<void>((_, reject) =>
      setTimeout(
        () => reject(
          new Error(
            'Gateway startup timeout (15s). Check if Python backend is working: python -m autoai.app.cli doctor'
          )
        ),
        TIMEOUTS.GATEWAY_STARTUP
      )
    );

    await Promise.race([startPromise, timeoutPromise]);
  } catch (error) {
    console.error('Failed to start gateway:', error instanceof Error ? error.message : error);
    console.error('');
    console.error('Troubleshooting:');
    console.error('  1. Run: python -m autoai.app.cli doctor');
    console.error('  2. Check .env: OPENAI_API_BASE_URL is reachable');
    console.error('  3. Try: python -m tui_gateway.entry');
    process.exit(1);
  }

  enterAlternateScreen();
  enableAlternateScroll();

  const saved = loadSession();
  if (saved) {
    restoreSession(saved);
  }

  startAutoSave(30000);

  instance = render(
    <ErrorBoundary level="root">
      <App gateway={gateway} />
    </ErrorBoundary>,
    {
      stdin: process.stdin,
      stdout: process.stdout,
      exitOnCtrlC: false,
      patchConsole: false,
    }
  );
}

main().catch(error => {
  logError('main', error);
  process.exit(1);
});
