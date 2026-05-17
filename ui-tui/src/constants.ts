// 键盘序列常量
export const KEY_SEQUENCES = {
  CTRL_C: '03',
  CTRL_D: '04',
  PAGE_UP_ALT: '1b5b357e',
  PAGE_UP_CTRL: '1b5b5e',
  PAGE_DOWN_ALT: '1b5b367e',
  PAGE_DOWN_3: '1b5b337e',
  UP_ARROW_SHIFT: '1b5b313b3241',
  UP_ARROW: '1b5b41',
  DOWN_ARROW_SHIFT: '1b5b313b3242',
  DOWN_ARROW: '1b5b42',
  LEFT_ARROW: '1b5b44',
  RIGHT_ARROW: '1b5b43',
  HOME: '1b5b48',
  END: '1b5b46',
  INSERT: '1b5b327e',
  DELETE: '1b5b337e',
  ESCAPE: '1b',
  MOUSE_PREFIX: '1b5b3c', // SGR鼠标模式前缀 ESC [ <
  MOUSE_CLICK_PREFIX: '1b4d', // 传统X10模式前缀 ESC M
  MOUSE_X10_EXT_PREFIX: '1b5b4d', // X10扩展模式前缀 ESC [ M
  MOUSE_ANY: '1b5b3c', // 任何以ESC [ < 开头的都是鼠标事件
} as const;

export const SCROLL_CONFIG = {
  STEP: 3,
  PAGE: 12,
  MOUSE_DELTA: 3,
} as const;

// 需要忽略的ANSI转义序列前缀（用于过滤未知控制序列）
export const ANSI_ESCAPE_PREFIXES = [
  '1b5b',   // ESC [ - CSI序列开始
  '1b5b3c', // ESC [ < - SGR鼠标
  '1b5b4d', // ESC [ M - X10扩展鼠标
  '1b5b3f', // ESC [ ? - DEC私有序列
  '1b5b3e', // ESC [ > - DEC私有序列
] as const;

// 超时配置
export const TIMEOUTS = {
  APPROVAL: 30, // 秒
  COMPLETION_REQUEST: 60, // 毫秒
  GATEWAY_STARTUP: 15000, // 毫秒
  RPC_REQUEST: Math.max(30000, Number.parseInt(process.env.TUI_RPC_TIMEOUT_MS || '120000', 10) || 120000),
} as const;

// 流节流配置
export const STREAM_THROTTLE_MS = 16;

// 视图配置
export const VIEWPORT_MESSAGE_LIMIT = 6;

// 日志配置
export const LOG_CONFIG = {
  MAX_LINES: 200,
  MAX_LINE_LENGTH: 4096,
} as const;

// 会话历史配置
export const HISTORY_CONFIG = {
  MAX_ITEMS: 100,
} as const;

// 输入限制配置
export const INPUT_LIMITS = {
  MAX_LENGTH: 10000,
  MAX_LINES: 100,
} as const;

// 重连配置
export const RECONNECT_CONFIG = {
  MAX_ATTEMPTS: 5,
  BASE_DELAY: 1000, // 毫秒
} as const;

// 审批选项
export const APPROVAL_CHOICES = ['once', 'session', 'always', 'deny'] as const;

export const APPROVAL_CHOICE_LABELS: Record<string, string> = {
  once: '本次同意',
  session: '本会话同意',
  always: '始终同意',
  deny: '拒绝',
} as const;

// 快速审批映射
export const QUICK_APPROVAL_MAP: Record<string, string> = {
  o: 'once',
  s: 'session',
  a: 'always',
  d: 'deny',
} as const;

// 模型设置步骤标签
export const MODEL_SETUP_STEP_LABELS: Record<string, string> = {
  base_url: '接口地址',
  api_key_env: '密钥环境变量',
  api_key: 'API 密钥',
  model: '模型型号',
} as const;

// 默认网关配置
export const DEFAULT_GATEWAY_CONFIG = {
  PYTHON: process.env.TUI_PYTHON || process.env.PYTHON || 'python',
  LANG: process.env.LANG || 'zh_CN.UTF-8',
  LC_ALL: process.env.LC_ALL || 'zh_CN.UTF-8',
  PYTHONIOENCODING: 'utf-8',
  PYTHONUTF8: '1',
} as const;
