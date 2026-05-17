export enum KeyType {
  MOUSE = 'mouse',
  CONTROL = 'control',
  NAVIGATION = 'navigation',
  PRINTABLE = 'printable',
  UNKNOWN = 'unknown',
}

export enum ControlKey {
  CTRL_C = 'c',
  CTRL_D = 'd',
  CTRL_L = 'l',
  CTRL_K = 'k',
}

export interface ParsedKey {
  seq: string;
  char: string;
  type: KeyType;
  isMouse: boolean;
  isCtrlC: boolean;
  isCtrlD: boolean;
  isEscape: boolean;
  isReturn: boolean;
  isBackspace: boolean;
  isTab: boolean;
  isUpArrow: boolean;
  isDownArrow: boolean;
  isPageUp: boolean;
  isPageDown: boolean;
  isDelete: boolean;
  isPrintable: boolean;
  ctrlChar: string | null;
  mouseButton?: number;
  mouseDelta?: number;
  mouseX?: number;
  mouseY?: number;
}

export interface InputContext {
  input: string;
  busy: boolean;
  overlayOpen: boolean;
  hasCompletions: boolean;
}

export type InputHandler = (key: ParsedKey, ctx: InputContext) => boolean;

export interface ScrollState {
  offset: number;
  max: number;
}

export interface ScrollHandler {
  handlePageUp(state: ScrollState): number;
  handlePageDown(state: ScrollState): number;
  handleLineUp(state: ScrollState): number;
  handleLineDown(state: ScrollState): number;
  handleDelta(state: ScrollState, delta: number): number;
}

export interface ScreenManager {
  enter(): void;
  exit(): void;
  enableScroll(): void;
  disableScroll(): void;
}

export interface RouterDeps {
  gateway: import('../gatewayClient.js').GatewayClient;
  exitApp: () => void;
}

export interface RouterConfig {
  debugInput?: boolean;
}
