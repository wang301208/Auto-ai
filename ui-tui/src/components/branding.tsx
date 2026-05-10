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
        {glyph.assistant} 本地智能体终端
      </Text>
      <Text color={theme.dim}>
        自主智能体 TUI | JSON-RPC 标准输入输出 | 全终端交互
      </Text>
      <Text color={theme.dim}>
        {info?.model || '本地运行时'} | {tools} 个工具 | {info?.cwd || process.cwd()}
      </Text>
    </Box>
  );
}


