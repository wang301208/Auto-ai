export const theme = {
  border: 'gray',
  dim: 'gray',
  text: 'white',
  user: 'green',
  assistant: 'cyan',
  label: 'magenta',
  ok: 'green',
  warn: 'yellow',
  error: 'red',
  prompt: 'cyan',
  tool: 'blue',
  colors: {
    primary: 'cyan',
    secondary: 'magenta',
    success: 'green',
    warning: 'yellow',
    error: 'red',
    info: 'blue',
    dim: 'gray'
  }
} as const;

export const glyph = {
  user: '>',
  assistant: '*',
  tool: '#',
  thinking: '...',
  queued: '.',
  rule: '-',
  cursor: '_'
} as const;

