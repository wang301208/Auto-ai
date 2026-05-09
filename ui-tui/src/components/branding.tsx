import React from 'react';
import { Box, Text } from 'ink';
import type { SessionInfo } from '../types.js';
import { glyph, theme } from '../theme.js';

export default function Branding({ info }: { info?: SessionInfo | null }) {
  const tools = info?.tools
    ? Object.values(info.tools).reduce((sum: number, items: string[]) => sum + items.length, 0)
    : 0;

  return (
    <Box flexDirection="column" paddingX={1} paddingTop={1}>
      <Text color={theme.assistant} bold>
        {glyph.assistant} Local Agent Terminal
      </Text>
      <Text color={theme.dim}>
        Autonomous agent TUI | JSON-RPC stdio | full terminal interaction
      </Text>
      <Text color={theme.dim}>
        {info?.model || 'local-runtime'} | {tools} tools | {info?.cwd || process.cwd()}
      </Text>
    </Box>
  );
}


