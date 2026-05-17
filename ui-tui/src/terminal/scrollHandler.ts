import { KEY_SEQUENCES, SCROLL_CONFIG } from '../constants.js';
import type { ScrollState, ScrollHandler } from './types.js';

export function createScrollHandler(config: typeof SCROLL_CONFIG = SCROLL_CONFIG): ScrollHandler {
  const clamp = (value: number, min: number, max: number): number => 
    Math.max(min, Math.min(max, value));

  return {
    handlePageUp(state: ScrollState): number {
      return clamp(state.offset + config.PAGE, 0, state.max);
    },

    handlePageDown(state: ScrollState): number {
      return clamp(state.offset - config.PAGE, 0, state.max);
    },

    handleLineUp(state: ScrollState): number {
      return clamp(state.offset + config.STEP, 0, state.max);
    },

    handleLineDown(state: ScrollState): number {
      return clamp(state.offset - config.STEP, 0, state.max);
    },

    handleDelta(state: ScrollState, delta: number): number {
      return clamp(state.offset + delta, 0, state.max);
    },
  };
}

export const defaultScrollHandler = createScrollHandler();
