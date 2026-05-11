import React from 'react';
import { render } from 'ink';
import App from './app.js';
import { GatewayClient } from './gatewayClient.js';

function enterAlternateScreen() {
  if (process.stdout.isTTY) {
    process.stdout.write('\x1b[?1049h\x1b[H\x1b[2J');
  }
}

function exitAlternateScreen() {
  if (process.stdout.isTTY) {
    process.stdout.write('\x1b[?1049l');
  }
}

function enableAlternateScroll() {
  if (process.stdout.isTTY) {
    process.stdout.write('\x1b[?1007h');
  }
}

function disableAlternateScroll() {
  if (process.stdout.isTTY) {
    process.stdout.write('\x1b[?1007l');
  }
}

async function main() {
  if (!process.stdin.isTTY) {
    console.error('Error: TUI requires an interactive TTY');
    process.exit(1);
  }

  const gateway = new GatewayClient();
  let cleanedUp = false;

  try {
    await gateway.start();
  } catch (error) {
    console.error('Failed to start gateway:', error);
    process.exit(1);
  }

  enterAlternateScreen();
  enableAlternateScroll();
  const instance = render(<App gateway={gateway} />);

  const cleanup = () => {
    if (cleanedUp) return;
    cleanedUp = true;
    instance.unmount();
    gateway.stop();
    disableAlternateScroll();
    exitAlternateScreen();
  };

  process.on('SIGINT', () => {
    cleanup();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    cleanup();
    process.exit(0);
  });
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});


