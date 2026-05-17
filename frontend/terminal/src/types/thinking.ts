import type { BilingualText } from './bilingual';

export enum ThinkingNodeType {
  ANALYSIS = 'analysis',
  DECISION = 'decision',
  RISK = 'risk',
  ACTION = 'action',
  WAIT = 'wait'
}

export enum ThinkingNodeState {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

export interface ThinkingNode {
  id: string;
  type: ThinkingNodeType;
  content: BilingualText;
  timestamp: string;
  parentId: string | null;
  state: ThinkingNodeState;
  details?: BilingualText;
  metadata?: Record<string, unknown>;
}

export interface ThinkingChainData {
  sessionId: string;
  nodes: ThinkingNode[];
  rootId: string;
  createdAt: string;
  updatedAt: string;
}

export interface ThinkingHistoryRecord {
  timestamp: string;
  nodeCount: number;
  duration: number;
  summary: BilingualText;
}

export interface ThinkingHistoryResponse {
  sessionId: string;
  records: ThinkingHistoryRecord[];
  total: number;
}
