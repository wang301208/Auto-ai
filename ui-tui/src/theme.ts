export const theme = {
  colors: {
    primary: 'cyan',
    secondary: 'magenta',
    success: 'green',
    warning: 'yellow',
    error: 'red',
    info: 'blue',
    dim: 'gray',
    border: 'gray',
    text: 'white',
    user: 'green',
    assistant: 'cyan',
    label: 'magenta',
    ok: 'green',
    warn: 'yellow',
    prompt: 'cyan',
    tool: 'blue',
  },
  glyphs: {
    user: '>',
    assistant: '*',
    tool: '#',
    thinking: '...',
    queued: '.',
    rule: '-',
    cursor: '_',
  },
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
} as const;

export const { colors } = theme;
export const { glyphs } = theme;
export const glyph = theme.glyphs;
