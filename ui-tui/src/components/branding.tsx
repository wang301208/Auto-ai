import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { glyph, theme } from '../theme.js';
import { sessionInfoAtom } from '../stores/sessionStore.js';

const Branding = React.memo(function Branding() {
  const info = useStore(sessionInfoAtom);
  const tools = info?.tools
    ? Object.values(info.tools).reduce((sum: number, items: string[]) => sum + items.length, 0)
    : 0;

  return (
    <Box flexDirection="column" paddingX={1} paddingTop={1}>
      <Text color={theme.colors.assistant} bold>
        {glyph.assistant} 本地智能体终端
      </Text>
      <Text color={theme.colors.dim}>
        自主智能体 TUI | JSON-RPC 标准输入输出 | 全终端交互
      </Text>
      <Text color={theme.colors.dim}>
        {info?.model || '本地运行时'} | {tools} 个工具 | {info?.cwd || process.cwd()}
      </Text>
    </Box>
  );
});

export default Branding;


