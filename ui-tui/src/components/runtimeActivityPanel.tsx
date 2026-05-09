import React from 'react';
import { Box, Text } from 'ink';
import type { ApprovalQueueItem, ContextCompaction, ParallelAgentRun, RuntimePlan, RuntimeRisk, RuntimeStep } from '../types.js';
import { theme } from '../theme.js';

function stepGlyph(status: RuntimeStep['status']) {
  if (status === 'complete') return 'v';
  if (status === 'running') return '>';
  if (status === 'error') return '!';
  return '-';
}

function stepColor(status: RuntimeStep['status']) {
  if (status === 'complete') return theme.ok;
  if (status === 'running') return theme.warn;
  if (status === 'error') return theme.error;
  return theme.dim;
}

function riskColor(risk?: RuntimeRisk | null) {
  if (!risk || risk.level === 'low') return theme.ok;
  if (risk.level === 'critical' || risk.level === 'high') return theme.error;
  return theme.warn;
}

export default function RuntimeActivityPanel({
  approvals,
  compaction,
  parallel,
  plan,
  risk,
  steps
}: {
  approvals: ApprovalQueueItem[];
  compaction?: ContextCompaction | null;
  parallel?: ParallelAgentRun | null;
  plan?: RuntimePlan | null;
  risk?: RuntimeRisk | null;
  steps: RuntimeStep[];
}) {
  const pendingApprovals = approvals.filter(item => item.status === 'pending');
  if (!plan && steps.length === 0 && pendingApprovals.length === 0 && !risk && !compaction && !parallel) return null;

  return (
    <Box borderColor={theme.border} borderStyle="round" flexDirection="column" marginTop={1} paddingX={1}>
      <Box>
        <Text bold color={theme.assistant}>
          Execution Steps
        </Text>
        {plan ? <Text color={theme.dim}> | {plan.title} | {plan.status}</Text> : null}
      </Box>

      {steps.slice(-6).map(step => (
        <Text color={stepColor(step.status)} key={step.id} wrap="truncate">
          {stepGlyph(step.status)} {step.title}
          {step.detail ? <Text color={theme.dim}> | {step.detail}</Text> : null}
          {step.parallel_group_id ? <Text color={theme.dim}> | {step.parallel_group_id}</Text> : null}
        </Text>
      ))}

      {parallel || risk || compaction ? (
        <Box flexDirection="column" marginTop={1}>
          <Text bold color={theme.label}>
            Runtime Signals
          </Text>
          {parallel ? (
            <Text color={parallel.status === 'error' ? theme.error : parallel.status === 'running' ? theme.warn : theme.ok} wrap="truncate">
              Parallel Agents: {parallel.completed ?? 0}/{parallel.total} complete
              <Text color={theme.dim}> | failed={parallel.failed ?? 0} | max_concurrency={parallel.max_concurrency ?? '-'}</Text>
            </Text>
          ) : null}
          {risk ? (
            <Text color={riskColor(risk)} wrap="truncate">
              Risk: {risk.level} <Text color={theme.dim}>| {risk.approval_policy}</Text>
            </Text>
          ) : null}
          {risk?.signals?.slice(0, 3).map(signal => (
            <Text color={theme.dim} key={signal} wrap="truncate">
              - {signal}
            </Text>
          ))}
          {compaction ? (
            <Text color={theme.dim} wrap="truncate">
              Context: {compaction.before_messages} -&gt; {compaction.after_messages} messages | {compaction.after_tokens} tokens | {compaction.trigger}
            </Text>
          ) : null}
        </Box>
      ) : null}

      {pendingApprovals.length ? (
        <Box flexDirection="column" marginTop={1}>
          <Text bold color={theme.warn}>
            Approvals
          </Text>
          {pendingApprovals.slice(0, 5).map(item => (
            <Text color={theme.warn} key={item.request_id} wrap="truncate">
              ! {item.title} <Text color={theme.dim}>({item.request_type}, risk={item.risk_level}, pending)</Text>
            </Text>
          ))}
        </Box>
      ) : null}
    </Box>
  );
}
