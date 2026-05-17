import { atom, computed } from 'nanostores';
import type { ToolActivity, RuntimePlan, RuntimeStep, RuntimeRisk, ApprovalQueueItem, AutonomyMaintenance, ParallelAgentRun, ContextCompaction, ContextFilesEvent, DevTaskUpdate, CronEvent, McpCallEvent, McpServerEvent } from '../types.js';

export const toolsAtom = atom<ToolActivity[]>([]);
export const runtimePlanAtom = atom<RuntimePlan | null>(null);
export const runtimeStepsAtom = atom<RuntimeStep[]>([]);
export const runtimeRiskAtom = atom<RuntimeRisk | null>(null);
export const autonomyMaintenanceAtom = atom<AutonomyMaintenance | null>(null);
export const parallelRunAtom = atom<ParallelAgentRun | null>(null);
export const contextCompactionAtom = atom<ContextCompaction | null>(null);
export const approvalsAtom = atom<ApprovalQueueItem[]>([]);
export const contextFilesAtom = atom<ContextFilesEvent | null>(null);
export const devTaskAtom = atom<DevTaskUpdate | null>(null);
export const cronEventsAtom = atom<CronEvent[]>([]);
export const mcpCallAtom = atom<McpCallEvent | null>(null);
export const mcpServersAtom = atom<McpServerEvent[]>([]);

export const activeToolCount = computed([toolsAtom], tools =>
  tools.filter(t => t.status === 'running').length
);

export const pendingApprovalCount = computed([approvalsAtom], approvals =>
  approvals.filter(a => a.status === 'pending').length
);

export const runningToolCount = computed([toolsAtom], tools =>
  tools.filter(t => t.status === 'running').length
);

export function addTool(tool: ToolActivity): void {
  toolsAtom.set([...toolsAtom.get(), tool]);
}

export function updateTool(toolId: string, update: Partial<ToolActivity>): void {
  toolsAtom.set(
    toolsAtom.get().map(t =>
      t.id === toolId ? { ...t, ...update } : t
    )
  );
}

export function updateToolByName(name: string, update: Partial<ToolActivity>): void {
  toolsAtom.set(
    toolsAtom.get().map(t =>
      t.name === name ? { ...t, ...update } : t
    )
  );
}

export function clearRuntime(): void {
  toolsAtom.set([]);
  runtimePlanAtom.set(null);
  runtimeStepsAtom.set([]);
  runtimeRiskAtom.set(null);
  autonomyMaintenanceAtom.set(null);
  parallelRunAtom.set(null);
  contextCompactionAtom.set(null);
  approvalsAtom.set([]);
  contextFilesAtom.set(null);
  devTaskAtom.set(null);
  cronEventsAtom.set([]);
  mcpCallAtom.set(null);
  mcpServersAtom.set([]);
}
