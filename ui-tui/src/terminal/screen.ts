const ANSI_CODES = {
  ALTERNATE_SCREEN_ENTER: '\x1b[?1049h\x1b[H\x1b[2J',
  ALTERNATE_SCREEN_EXIT: '\x1b[?1049l',
  ALTERNATE_SCROLL_ENABLE: '\x1b[?1007h',
  ALTERNATE_SCROLL_DISABLE: '\x1b[?1007l',
} as const;

import type { ScreenManager } from './types.js';

export function createScreenManager(
  stream: NodeJS.WriteStream & { isTTY?: boolean } = process.stdout
): ScreenManager {
  const isTTY = stream.isTTY === true;

  const writeIfTTY = (code: string): void => {
    if (isTTY) {
      stream.write(code);
    }
  };

  return {
    enter(): void {
      writeIfTTY(ANSI_CODES.ALTERNATE_SCREEN_ENTER);
    },

    exit(): void {
      writeIfTTY(ANSI_CODES.ALTERNATE_SCREEN_EXIT);
    },

    enableScroll(): void {
      writeIfTTY(ANSI_CODES.ALTERNATE_SCROLL_ENABLE);
    },

    disableScroll(): void {
      writeIfTTY(ANSI_CODES.ALTERNATE_SCROLL_DISABLE);
    },
  };
}

export const defaultScreenManager = createScreenManager();

export function enterAlternateScreen(): void {
  defaultScreenManager.enter();
}

export function exitAlternateScreen(): void {
  defaultScreenManager.exit();
}

export function enableAlternateScroll(): void {
  defaultScreenManager.enableScroll();
}

export function disableAlternateScroll(): void {
  defaultScreenManager.disableScroll();
}
