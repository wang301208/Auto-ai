import React from 'react';
import { Box, Text } from 'ink';
import { theme, glyph } from '../theme.js';
import type { TranscriptMessage } from '../types.js';

interface Props {
  message: TranscriptMessage;
  isStreaming?: boolean;
  compact?: boolean;
}

const ROLE_STYLE: Record<string, { color: string; prefix: string }> = {
  user:      { color: theme.colors.user,      prefix: glyph.user },
  assistant: { color: theme.colors.assistant, prefix: glyph.assistant },
  system:    { color: theme.colors.dim,       prefix: '' },
  tool:      { color: theme.colors.tool,      prefix: glyph.tool },
};

const MessageLine = React.memo(function MessageLine({
  message,
  isStreaming = false,
  compact = false,
}: Props) {
  const style = ROLE_STYLE[message.role] || { color: theme.colors.text, prefix: '' };

  const displayText = compact && message.text.length > 200
    ? `${message.text.slice(0, 200)}...`
    : message.text;

  const content = `${style.prefix ? style.prefix + ' ' : ''}${displayText}${isStreaming ? '▌' : ''}`;

  return (
    <Box flexDirection="column" marginBottom={compact ? 0 : 1}>
      <Text color={style.color} bold={!!style.prefix} wrap="wrap">
        {content}
      </Text>
    </Box>
  );
});

export default MessageLine;
