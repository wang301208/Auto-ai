import React from 'react';
import { Box, Text } from 'ink';
import type { SessionInfo, ToolActivity, Usage } from '../types.js';
import { theme } from '../theme.js';

interface Props {
  busy: boolean;
  info?: SessionInfo | null;
  queueCount: number;
  status: string;
  tools: ToolActivity[];
  usage?: Usage;
}

export default function StatusBar({ busy, info, queueCount, status, tools, usage }: Props) {
  const activeTools = tools.filter(tool => tool.status === 'running').length;
  const model = info?.model || 'local-runtime';
  const tokens = usage?.total ?? info?.usage?.total ?? 0;
  const cost = usage?.cost_usd ?? info?.usage?.cost_usd ?? 0;

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color={theme.border}>{'-'.repeat(80)}</Text>
      <Box>
        <Text color={busy ? theme.warn : theme.ok}>{busy ? 'busy' : 'idle'}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{model}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{tokens} tokens</Text>
        <Text color={theme.dim}> | </Text>
        <Text>${cost.toFixed(4)}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{activeTools} tools</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{queueCount} queued</Text>
        <Text color={theme.dim}> | </Text>
        <Text color={theme.dim}>{status}</Text>
      </Box>
    </Box>
  );
}
