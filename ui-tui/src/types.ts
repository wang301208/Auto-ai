export interface Usage {
  input?: number;
  output?: number;
  total?: number;
  cost_usd?: number;
  context_used?: number;
  context_max?: number;
  context_percent?: number;
}

export interface SessionInfo {
  id?: string;
  model?: string;
  reasoning_effort?: string;
  service_tier?: string;
  fast?: boolean;
  tools?: Record<string, string[]>;
  skills?: Record<string, unknown>;
  cwd?: string;
  version?: string;
  release_date?: string;
  usage?: Usage;
}

export interface CompletionItem {
  text: string;
  display?: string;
  meta?: string;
}

export interface TranscriptMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  text: string;
  timestamp: number;
  kind?: 'intro' | 'message' | 'panel';
}

export interface ToolActivity {
  id: string;
  name: string;
  status: 'running' | 'complete' | 'error';
  context?: string;
  preview?: string;
  summary?: string;
  error?: string;
  startedAt: number;
  parallel_group_id?: string;
}

export interface RuntimeStep {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  detail?: string;
  parallel_group_id?: string;
}

export interface RuntimePlan {
  plan_id: string;
  title: string;
  status: 'running' | 'complete' | 'error';
  steps: RuntimeStep[];
}

export interface ApprovalQueueItem {
  request_id: string;
  request_type: string;
  title: string;
  risk_level: string;
  status: string;
  requested_by?: string;
}

export interface RuntimeRisk {
  level: 'low' | 'medium' | 'high' | 'critical' | string;
  signals: string[];
  approval_policy: string;
  pending_approvals?: string[];
}

export interface ContextCompaction {
  trigger: string;
  before_messages: number;
  after_messages: number;
  removed_messages: number;
  before_tokens: number;
  after_tokens: number;
  context_percent: number;
  summary?: {
    headline?: string;
    noop?: boolean;
    token_line?: string;
  };
}

export interface ParallelAgentRun {
  parallel_group_id: string;
  total: number;
  completed?: number;
  failed?: number;
  max_concurrency?: number;
  status: 'running' | 'complete' | 'error';
}

export type OverlayState =
  | { type: 'none' }
  | { type: 'approval'; command?: string; description?: string; request_id?: string; selected: number; timeout_remaining?: number }
  | { type: 'clarify'; request_id: string; question: string; choices: string[] | null; selected: number; value: string; freeText: boolean }
  | { type: 'sudo'; request_id: string; value: string }
  | { type: 'secret'; request_id: string; env_var: string; prompt: string; value: string }
  | { type: 'sessionPicker'; selected: number; sessions: SessionListItem[] }
  | { type: 'modelPicker'; selected: number; providers: ModelProvider[] };

export interface SessionListItem {
  id: string;
  title: string;
  preview?: string;
  started_at?: number;
  message_count?: number;
  source?: string;
}

export interface ModelProvider {
  name: string;
  slug: string;
  authenticated?: boolean;
  is_current?: boolean;
  models?: string[];
  status?: string;
  base_url?: string;
  api_key_env?: string;
  dry_run?: boolean;
  reason?: string;
}


