export type PlatformTier =
  | "tty"
  | "ci"
  | "cli-no-tty"
  | "browser"
  | "browser-headless"
  | "browser-ssr"
  | "browser-web-terminal"
  | "electron"
  | "electron-headless"
  | "tauri"
  | "unknown";

export interface EnvironmentDetection {
  tier: PlatformTier;
  isTTY: boolean;
  isBrowser: boolean;
  isHeadless: boolean;
  isDesktop: boolean;
  isCI: boolean;
  isWebTerminal: boolean;
  details: Record<string, unknown>;
}

export function detectEnvironment(): EnvironmentDetection {
  if (isNodeLike()) {
    return detectNodeEnvironment();
  }
  if (isBrowserLike()) {
    return detectBrowserEnvironment();
  }
  return {
    tier: "unknown",
    isTTY: false,
    isBrowser: false,
    isHeadless: false,
    isDesktop: false,
    isCI: false,
    isWebTerminal: false,
    details: {},
  };
}

function isNodeLike(): boolean {
  return (
    typeof process !== "undefined" &&
    process !== null &&
    typeof process.versions === "object" &&
    process.versions !== null &&
    "node" in process.versions
  );
}

function isBrowserLike(): boolean {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

// ─── Node.js / CLI 环境 ───────────────────────────────────────

function detectNodeEnvironment(): EnvironmentDetection {
  const isTTY = !!(process.stdout as { isTTY?: boolean })?.isTTY;
  const isCI = detectCI();
  const term = process.env.TERM ?? "";
  const termProgram = process.env.TERM_PROGRAM ?? "";
  const colorTerm = process.env.COLORTERM ?? "";
  const colortFgbg = process.env.COLORFGBG ?? "";
  const shell = process.env.SHELL ?? process.env.ComSpec ?? "";

  const details: Record<string, unknown> = {
    isTTY,
    term,
    termProgram,
    colorTerm,
    colorFgbg: colortFgbg,
    shell,
    platform: process.platform,
    nodeVersion: process.versions.node,
    isElectron: !!process.versions.electron,
    isTauri: false,
  };

  if (isCI) {
    return {
      tier: "ci",
      isTTY: false,
      isBrowser: false,
      isHeadless: true,
      isDesktop: false,
      isCI: true,
      isWebTerminal: false,
      details,
    };
  }

  if (process.versions.electron) {
    return {
      tier: "electron",
      isTTY: false,
      isBrowser: false,
      isHeadless: false,
      isDesktop: true,
      isCI: false,
      isWebTerminal: false,
      details,
    };
  }

  if (isTTY) {
    return {
      tier: "tty",
      isTTY: true,
      isBrowser: false,
      isHeadless: false,
      isDesktop: false,
      isCI: false,
      isWebTerminal: false,
      details,
    };
  }

  return {
    tier: "cli-no-tty",
    isTTY: false,
    isBrowser: false,
    isHeadless: true,
    isDesktop: false,
    isCI: false,
    isWebTerminal: false,
    details,
  };
}

function detectCI(): boolean {
  if (process.env.CI) return true;
  if (process.env.GITHUB_ACTIONS) return true;
  if (process.env.GITLAB_CI) return true;
  if (process.env.TRAVIS) return true;
  if (process.env.CIRCLECI) return true;
  if (process.env.JENKINS_URL) return true;
  if (process.env.BUILDKITE) return true;
  if (process.env.BUILD_ID) return true;
  if (process.env.TF_BUILD) return true;
  if (process.env.RUN_ID) return true;
  return false;
}

// ─── Web 前端环境 ─────────────────────────────────────────────

function detectBrowserEnvironment(): EnvironmentDetection {
  const ua = navigator.userAgent;
  const isHeadless = detectHeadlessBrowser(ua);
  const isSSR = detectSSR();
  const isWebTerminal = detectWebTerminal();
  const isTauri = detectTauri();
  const isElectron = detectElectron(ua);

  const details: Record<string, unknown> = {
    userAgent: ua,
    language: navigator.language,
    colorScheme: matchColorScheme(),
    colorDepth: screen?.colorDepth,
    devicePixelRatio: window.devicePixelRatio,
    isTauri,
    isElectron,
    isWebTerminal,
    isHeadless,
    isSSR,
    hasTouchSupport: "ontouchstart" in window,
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
  };

  let tier: PlatformTier = "browser";

  if (isTauri) {
    tier = "tauri";
  } else if (isElectron && isHeadless) {
    tier = "electron-headless";
  } else if (isElectron) {
    tier = "electron";
  } else if (isSSR) {
    tier = "browser-ssr";
  } else if (isHeadless) {
    tier = "browser-headless";
  } else if (isWebTerminal) {
    tier = "browser-web-terminal";
  }

  return {
    tier,
    isTTY: false,
    isBrowser: true,
    isHeadless,
    isDesktop: isTauri || isElectron,
    isCI: false,
    isWebTerminal,
    details,
  };
}

function detectHeadlessBrowser(ua: string): boolean {
  if (/HeadlessChrome/i.test(ua)) return true;
  if (/PhantomJS/i.test(ua)) return true;
  if (/SlimerJS/i.test(ua)) return true;

  if (!navigator.webdriver) {
    // webdriver=false 不代表非无头，但 webdriver=true 一定无头
  } else {
    return true;
  }

  try {
    if (navigator.plugins && navigator.plugins.length === 0 && !/Chrome/i.test(ua)) {
      // 无插件 + 非 Chrome 可疑，但不确凿
    }
  } catch {
    // 不做判断
  }

  // Puppeteer/Playwright 注入的标志
  if ((window as Record<string, unknown>).__puppeteer_evaluation_script__) return true;
  if ((window as Record<string, unknown>).__playwright) return true;

  // CDP 连接标志
  if ((window as Record<string, unknown>).__cdp__) return true;

  return false;
}

function detectSSR(): boolean {
  // SSR 水合环境中 DOM 可用但部分 API 不完整
  if (typeof window !== "undefined" && !window.requestAnimationFrame) return true;
  if (typeof window !== "undefined" && !window.IntersectionObserver) return true;
  return false;
}

function detectWebTerminal(): boolean {
  // xterm.js 实例检测
  if ((window as Record<string, unknown>).Terminal) return true;
  if ((window as Record<string, unknown>).__XTERM_INSTANCE__) return true;

  // DOM 中查找 xterm 容器
  try {
    if (document.querySelector(".xterm")) return true;
    if (document.querySelector("[data-terminal]")) return true;
  } catch {
    // ignore
  }

  // 终端 URL scheme
  if (window.location.pathname.includes("/terminal")) return true;

  return false;
}

function detectTauri(): boolean {
  // Tauri v2
  if ((window as Record<string, unknown>).__TAURI_INTERNALS__) return true;
  // Tauri v1
  if ((window as Record<string, unknown>).__TAURI__) return true;
  // Tauri IPC 通道
  if ((window as Record<string, unknown>).__TAURI_IPC__) return true;
  return false;
}

function detectElectron(ua: string): boolean {
  if (/Electron/i.test(ua)) return true;
  if (typeof process !== "undefined" && process?.versions?.electron) return true;
  return false;
}

function matchColorScheme(): "dark" | "light" | "no-preference" {
  if (!window.matchMedia) return "no-preference";
  if (window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
  if (window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
  return "no-preference";
}

// ─── 便捷谓词 ─────────────────────────────────────────────────

export function isInteractiveTerminal(): boolean {
  const env = detectEnvironment();
  return env.tier === "tty" || env.tier === "browser-web-terminal";
}

export function isRealTTY(): boolean {
  if (isNodeLike()) {
    return !!(process.stdout as { isTTY?: boolean })?.isTTY;
  }
  return false;
}

export function isDesktopApp(): boolean {
  const env = detectEnvironment();
  return env.isDesktop;
}

export function isHeadless(): boolean {
  return detectEnvironment().isHeadless;
}

export function supportsColor(): boolean {
  if (isNodeLike()) {
    if (process.env.FORCE_COLOR) return true;
    if (process.env.NO_COLOR) return false;
    if ((process.stdout as { isTTY?: boolean })?.isTTY) return true;
    if (process.env.COLORTERM) return true;
    if (process.env.TERM && /-256color/.test(process.env.TERM)) return true;
    return false;
  }
  if (isBrowserLike()) {
    return !!screen?.colorDepth && screen.colorDepth >= 8;
  }
  return false;
}

export function supportsTrueColor(): boolean {
  if (isNodeLike()) {
    if (process.env.COLORTERM === "truecolor" || process.env.COLORTERM === "24bit") return true;
    if (process.env.TERM === "xterm-truecolor") return true;
    return false;
  }
  if (isBrowserLike()) {
    return !!screen?.colorDepth && screen.colorDepth >= 24;
  }
  return false;
}

// ─── 终端能力检测（Hermes-style 5-layer） ────────────────────

export function detectTerminalLightMode(): boolean | null {
  if (!isNodeLike()) return null;

  // 层1：环境变量强制覆盖
  const forceLight = process.env.DUAL_RING_TUI_LIGHT;
  if (forceLight !== undefined) return forceLight === "1" || forceLight === "true";

  // 层2：命名主题
  const theme = process.env.DUAL_RING_TUI_THEME;
  if (theme === "light") return true;
  if (theme === "dark") return false;

  // 层3：背景色 Rec.709 亮度
  const bg = process.env.DUAL_RING_TUI_BACKGROUND;
  if (bg && /^#[0-9a-fA-F]{6}$/.test(bg)) {
    const r = parseInt(bg.slice(1, 3), 16);
    const g = parseInt(bg.slice(3, 5), 16);
    const b = parseInt(bg.slice(5, 7), 16);
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > 0.5;
  }

  // 层4：COLORFGBG 色槽
  const cfg = process.env.COLORFGBG;
  if (cfg && cfg.includes(";")) {
    const bgSlot = parseInt(cfg.split(";")[1], 10);
    if (!isNaN(bgSlot)) return bgSlot >= 8;
  }

  // 层5：TERM_PROGRAM 白名单
  const lightTerminals = new Set(["Apple_Terminal", "macOS"]);
  const tp = process.env.TERM_PROGRAM;
  if (tp) return lightTerminals.has(tp);

  return null;
}
