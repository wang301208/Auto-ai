export { parseKey, KNOWN_CSI_SEQUENCES } from './keyParser.js';
export { createInputRouter } from './inputRouter.js';
export {
  createScreenManager,
  defaultScreenManager,
  enterAlternateScreen,
  exitAlternateScreen,
  enableAlternateScroll,
  disableAlternateScroll,
} from './screen.js';
export { createScrollHandler, defaultScrollHandler } from './scrollHandler.js';
export { KeyType } from './types.js';
export type {
  ParsedKey,
  InputContext,
  InputHandler,
  ScrollState,
  ScrollHandler,
  ScreenManager,
  RouterDeps,
  RouterConfig,
} from './types.js';
