import React from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import { theme } from '../theme.js';
import { sessionInfoAtom, usageAtom, busyAtom, statusAtom } from '../stores/index.js';
import { queueCount } from '../stores/inputStore.js';
import { runningToolCount } from '../stores/runtimeStore.js';
import type { SessionStatus } from '../stores/sessionStore.js';

const STATUS_LABEL: Record<string, string> = {
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
  'parallel errors': '并行错误',
};

export default function StatusBar() {
  const info = useStore(sessionInfoAtom);
  const usage = useStore(usageAtom);
  const busy = useStore(busyAtom);
  const status = useStore(statusAtom);
  const activeTools = useStore(runningToolCount);
  const qCount = useStore(queueCount);

  const model = info?.model || '本地运行时';
  const tokens = usage?.total ?? info?.usage?.total ?? 0;
  const cost = usage?.cost_usd ?? info?.usage?.cost_usd ?? 0;

  return (
    <Box flexDirection="column" marginTop={1}>
      <Text color={theme.colors.border}>{'-'.repeat(80)}</Text>
      <Box>
        <Text color={busy ? theme.colors.warning : theme.colors.ok}>{busy ? '忙碌' : '空闲'}</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text>{model}</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text>{tokens} 令牌</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text>${cost.toFixed(4)}</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text>{activeTools} 个工具运行中</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text>{qCount} 个排队</Text>
        <Text color={theme.colors.dim}> | </Text>
        <Text color={theme.colors.dim}>{STATUS_LABEL[status] || status}</Text>
      </Box>
    </Box>
  );
}
