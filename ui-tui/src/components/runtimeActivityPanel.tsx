import React, { useMemo } from 'react';
import { Box, Text } from 'ink';
import { useStore } from '@nanostores/react';
import type {
  ApprovalQueueItem,
  AutonomyMaintenance,
  ContextCompaction,
  ParallelAgentRun,
  RuntimePlan,
  RuntimeRisk,
  RuntimeStep
} from '../types.js';
import { theme } from '../theme.js';
import { runtimePlanAtom, runtimeStepsAtom, runtimeRiskAtom, autonomyMaintenanceAtom, parallelRunAtom, contextCompactionAtom, approvalsAtom } from '../stores/runtimeStore.js';

function stepGlyph(status: RuntimeStep['status']) {
  if (status === 'complete') return 'v';
  if (status === 'running') return '>';
  if (status === 'error') return '!';
  return '-';
}

function stepColor(status: RuntimeStep['status']) {
  if (status === 'complete') return theme.colors.ok;
  if (status === 'running') return theme.colors.warn;
  if (status === 'error') return theme.colors.error;
  return theme.colors.dim;
}

function riskColor(risk?: RuntimeRisk | null) {
  if (!risk || risk.level === 'low') return theme.colors.ok;
  if (risk.level === 'critical' || risk.level === 'high') return theme.colors.error;
  return theme.colors.warn;
}

function statusText(status: string) {
  return (
    {
      pending: '等待中',
      running: '运行中',
      complete: '完成',
      completed: '完成',
      error: '错误',
      low: '低',
      medium: '中',
      high: '高',
      critical: '严重'
    } as Record<string, string>
  )[status] || status;
}

function RuntimeActivityPanelBase() {
  const plan = useStore(runtimePlanAtom);
  const steps = useStore(runtimeStepsAtom);
  const risk = useStore(runtimeRiskAtom);
  const maintenance = useStore(autonomyMaintenanceAtom);
  const parallel = useStore(parallelRunAtom);
  const compaction = useStore(contextCompactionAtom);
  const approvals = useStore(approvalsAtom);
  
  const pendingApprovals = useMemo(
    () => approvals.filter(item => item.status === 'pending'),
    [approvals]
  );
  
  const visibleSteps = useMemo(
    () => steps.slice(-6),
    [steps]
  );
  
  const maintenanceStats = useMemo(() => {
    if (!maintenance?.actions) return { completed: 0, errors: 0 };
    return {
      completed: maintenance.actions.filter(item => item.status === 'completed').length,
      errors: maintenance.actions.filter(item => item.status === 'error').length,
    };
  }, [maintenance]);
  
  if (!plan && steps.length === 0 && pendingApprovals.length === 0 && !risk && !compaction && !parallel && !maintenance) return null;

  return (
    <Box borderColor={theme.colors.border} borderStyle="round" flexDirection="column" marginTop={1} paddingX={1}>
      <Box>
        <Text bold color={theme.colors.assistant}>
          执行步骤
        </Text>
        {plan ? <Text color={theme.colors.dim}> | {plan.title} | {statusText(plan.status)}</Text> : null}
      </Box>

      {visibleSteps.map(step => (
        <Text color={stepColor(step.status)} key={step.id} wrap="truncate">
          {stepGlyph(step.status)} {step.title}
          {step.detail ? <Text color={theme.colors.dim}> | {step.detail}</Text> : null}
          {step.parallel_group_id ? <Text color={theme.colors.dim}> | {step.parallel_group_id}</Text> : null}
        </Text>
      ))}

      {parallel || risk || compaction || maintenance ? (
        <Box flexDirection="column" marginTop={1}>
          <Text bold color={theme.colors.label}>
            运行信号
          </Text>
          {maintenance ? (
            <Text color={maintenanceStats.errors ? theme.colors.warn : theme.colors.ok} wrap="truncate">
              自主自我：{maintenance.trigger === 'session_start' ? '已启动' : '已维护'}
              <Text color={theme.colors.dim}>
                {' '}| 完成={maintenanceStats.completed} | 异常={maintenanceStats.errors} | 目标={maintenance.self_state?.active_goal || maintenance.trigger}
              </Text>
            </Text>
          ) : null}
          {parallel ? (
            <Text color={parallel.status === 'error' ? theme.colors.error : parallel.status === 'running' ? theme.colors.warn : theme.colors.ok} wrap="truncate">
              并行智能体：{parallel.completed ?? 0}/{parallel.total} 完成
              <Text color={theme.colors.dim}> | 失败={parallel.failed ?? 0} | 最大并发={parallel.max_concurrency ?? '-'}</Text>
            </Text>
          ) : null}
          {risk ? (
            <Text color={riskColor(risk)} wrap="truncate">
              风险：{statusText(risk.level)} <Text color={theme.colors.dim}>| {risk.approval_policy}</Text>
            </Text>
          ) : null}
          {risk?.signals?.slice(0, 3).map(signal => (
            <Text color={theme.colors.dim} key={signal} wrap="truncate">
              - {signal}
            </Text>
          ))}
          {compaction ? (
            <Text color={theme.colors.dim} wrap="truncate">
              上下文：{compaction.before_messages} 到 {compaction.after_messages} 条消息 | {compaction.after_tokens} 令牌 | {compaction.trigger}
            </Text>
          ) : null}
        </Box>
      ) : null}

      {pendingApprovals.length ? (
        <Box flexDirection="column" marginTop={1}>
          <Text bold color={theme.colors.warn}>
            审批
          </Text>
          {pendingApprovals.slice(0, 5).map(item => (
            <Text color={theme.colors.warn} key={item.request_id} wrap="truncate">
              ! {item.title} <Text color={theme.colors.dim}>({item.request_type}, 风险={statusText(item.risk_level)}, 待审批)</Text>
            </Text>
          ))}
        </Box>
      ) : null}
    </Box>
  );
}

export default React.memo(RuntimeActivityPanelBase);
