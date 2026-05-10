import React from 'react';
import { Box, Text } from 'ink';
import type { TranscriptMessage } from '../types.js';
import { glyph, theme } from '../theme.js';

interface Props {
  compact?: boolean;
  isStreaming?: boolean;
  message: TranscriptMessage;
}

const roleStyle = {
  user: { color: theme.user, label: '你', mark: glyph.user },
  assistant: { color: theme.assistant, label: '助手', mark: glyph.assistant },
  system: { color: theme.warn, label: '系统', mark: '!' },
  tool: { color: theme.tool, label: '工具', mark: glyph.tool }
} as const;

export default function MessageLine({ compact = false, isStreaming = false, message }: Props) {
  const style = roleStyle[message.role];

  return (
    <Box flexDirection="column" marginTop={compact ? 0 : 1}>
      <Box>
        <Text color={style.color} bold>
          {style.mark} {style.label}
        </Text>
        {isStreaming ? <Text color={theme.dim}> 正在输出</Text> : null}
      </Box>
      <Box paddingLeft={2}>
        <Text wrap="wrap">
          {message.text}
          {isStreaming ? <Text color={theme.prompt}> {glyph.cursor}</Text> : null}
        </Text>
      </Box>
    </Box>
  );
}


