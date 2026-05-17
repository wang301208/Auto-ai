import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import type { ToolActivity } from '../types.js';
import { glyph, theme } from '../theme.js';
import { toolsAtom } from '../stores/runtimeStore.js';

const ToolActivityPanel = React.memo(function ToolActivityPanel() {
  const tools = useStore(toolsAtom);
  const visible = tools.slice(-5);
  if (!visible.length) return null;
  const statusText: Record<ToolActivity['status'], string> = {
    running: '运行中',
    complete: '完成',
    error: '错误'
  };

  return (
    <Box flexDirection="column" marginTop={1}>
      {visible.map(tool => (
        <Text color={tool.status === 'error' ? theme.colors.error : tool.status === 'running' ? theme.colors.warn : theme.colors.dim} key={tool.id}>
          {glyph.tool} {tool.name} {statusText[tool.status]}
          {tool.context ? <Text color={theme.colors.dim}> | {tool.context}</Text> : null}
          {tool.parallel_group_id ? <Text color={theme.colors.dim}> | {tool.parallel_group_id}</Text> : null}
          {tool.preview ? <Text color={theme.colors.dim}> | {tool.preview}</Text> : null}
          {tool.summary ? <Text color={theme.colors.dim}> | {tool.summary}</Text> : null}
          {tool.error ? <Text color={theme.colors.error}> | {tool.error}</Text> : null}
        </Text>
      ))}
    </Box>
  );
});

export default ToolActivityPanel;


