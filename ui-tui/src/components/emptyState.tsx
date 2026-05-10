import React from 'react';
import { Box, Text } from 'ink';
import type { SessionInfo } from '../types.js';
import { glyph, theme } from '../theme.js';

function toolCount(info?: SessionInfo | null) {
  return info?.tools
    ? Object.values(info.tools).reduce((sum: number, items: string[]) => sum + items.length, 0)
    : 0;
}

const asciiArt = [
  '    /\\',
  '   /  \\',
  '  / /\\ \\',
  ' / ____ \\',
  '/_/    \\_\\',
  '  本地',
  ' 智能体'
];

export default function EmptyState({ info }: { info?: SessionInfo | null }) {
  const tools = toolCount(info);
  const cwd = info?.cwd || process.cwd();
  const model = info?.model || '本地运行时';

  return (
    <Box flexDirection="column" paddingTop={1}>
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color={theme.assistant}>
          {glyph.assistant} 本地智能体
        </Text>
        <Text color={theme.dim}>自主运行时终端</Text>
      </Box>

      <Box borderColor={theme.border} borderStyle="round" flexDirection="row" paddingX={2} paddingY={1}>
        <Box flexDirection="column" marginRight={4} width={14}>
          {asciiArt.map((line, index) => (
            <Text color={index < 5 ? theme.assistant : theme.dim} key={`${index}:${line}`}>
              {line}
            </Text>
          ))}
          <Text />
          <Text color={theme.dim} wrap="truncate-end">
            {model}
          </Text>
          <Text color={theme.dim} wrap="truncate-end">
            {cwd}
          </Text>
        </Box>

        <Box flexDirection="column" width={62}>
          <Box flexDirection="column">
            <Text bold color={theme.prompt}>
              {glyph.cursor} 自然语言交互
            </Text>
            <Text color={theme.text} wrap="truncate">
              直接说出目标、约束和期望结果
            </Text>
            <Text color={theme.dim} wrap="truncate">
              需要文件、模型、工具或系统操作时会自动选择路径
            </Text>
          </Box>

          <Box flexDirection="column" marginTop={1}>
            <Text bold color={theme.prompt}>
              {glyph.cursor} 自动处理
            </Text>
            <Text color={theme.text} wrap="truncate">
              风险操作会弹出审批，长对话会自动压缩上下文
            </Text>
            <Text color={theme.dim} wrap="truncate">
              TUI → Python 网关 → 标准输入输出 JSON-RPC | {tools || 0} 个能力已接入
            </Text>
          </Box>

          <Text color={theme.dim}>
            输入自然语言即可开始
          </Text>
        </Box>
      </Box>
    </Box>
  );
}
