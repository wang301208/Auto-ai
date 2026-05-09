import React from 'react';
import { Box, Text } from 'ink';
import type { ToolActivity } from '../types.js';
import { glyph, theme } from '../theme.js';

export default function ToolActivityPanel({ tools }: { tools: ToolActivity[] }) {
  const visible = tools.slice(-5);
  if (!visible.length) return null;

  return (
    <Box flexDirection="column" marginTop={1}>
      {visible.map(tool => (
        <Text color={tool.status === 'error' ? theme.error : tool.status === 'running' ? theme.warn : theme.dim} key={tool.id}>
          {glyph.tool} {tool.name} {tool.status}
          {tool.context ? <Text color={theme.dim}> | {tool.context}</Text> : null}
          {tool.parallel_group_id ? <Text color={theme.dim}> | {tool.parallel_group_id}</Text> : null}
          {tool.preview ? <Text color={theme.dim}> | {tool.preview}</Text> : null}
          {tool.summary ? <Text color={theme.dim}> | {tool.summary}</Text> : null}
          {tool.error ? <Text color={theme.error}> | {tool.error}</Text> : null}
        </Text>
      ))}
    </Box>
  );
}


