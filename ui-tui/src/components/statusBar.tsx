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
  const model = info?.model || '本地运行时';
  const tokens = usage?.total ?? info?.usage?.total ?? 0;
  const cost = usage?.cost_usd ?? info?.usage?.cost_usd ?? 0;
  const statusText: Record<string, string> = {
    starting: '启动中',
    ready: '就绪',
    running: '运行中',
    streaming: '流式输出',
    queued: '已排队',
    error: '错误',
    interrupted: '已中断',
    'gateway log': '网关日志',
    'context compacted': '上下文已压缩',
    'parallel agents': '并行智能体',
    'parallel complete': '并行完成',
    'parallel errors': '并行错误'
  };

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color={theme.border}>{'-'.repeat(80)}</Text>
      <Box>
        <Text color={busy ? theme.warn : theme.ok}>{busy ? '忙碌' : '空闲'}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{model}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{tokens} 令牌</Text>
        <Text color={theme.dim}> | </Text>
        <Text>${cost.toFixed(4)}</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{activeTools} 个工具运行中</Text>
        <Text color={theme.dim}> | </Text>
        <Text>{queueCount} 个排队</Text>
        <Text color={theme.dim}> | </Text>
        <Text color={theme.dim}>{statusText[status] || status}</Text>
      </Box>
    </Box>
  );
}
