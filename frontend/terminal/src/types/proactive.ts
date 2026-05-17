import type { BilingualText } from './bilingual';

export enum SuggestionType {
  ACTION_SUGGESTION = 'action_suggestion',
  RESOURCE_NEGOTIATION = 'resource_negotiation',
  OPTIMIZATION_TIP = 'optimization_tip'
}

export enum SuggestionPriority {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

export enum SuggestionAction {
  CONFIRM = 'confirm',
  REJECT = 'reject',
  NEGOTIATE = 'negotiate'
}

export interface SuggestionOption {
  action: SuggestionAction;
  label: BilingualText;
  description?: BilingualText;
}

export interface ProactiveSuggestion {
  id: string;
  type: SuggestionType;
  content: BilingualText;
  expectedEffect: BilingualText;
  options: SuggestionOption[];
  priority: SuggestionPriority;
  validUntil: string;
  createdAt: string;
  requiresApproval?: boolean;
  metadata?: Record<string, unknown>;
}

export enum ResourceType {
  COMPUTE_RESOURCE = 'compute_resource',
  API_QUOTA = 'api_quota',
  EXECUTION_TIME = 'execution_time'
}

export interface ResourceAmount {
  value: number;
  unit: string;
}

export interface UsageEstimate {
  estimatedTime: string;
  expectedConsumption: BilingualText;
}

export enum NegotiationStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  REJECTED = 'rejected',
  MODIFIED = 'modified'
}

export interface ResourceNegotiation {
  id: string;
  resourceType: ResourceType;
  requestedAmount: ResourceAmount;
  usageEstimate: UsageEstimate;
  impactAnalysis: BilingualText;
  options: SuggestionOption[];
  status: NegotiationStatus;
  createdAt: string;
  respondedAt?: string;
}

export interface SuggestionResponse {
  suggestionId: string;
  action: SuggestionAction;
  negotiatedContent?: string;
  timestamp: string;
}

export interface NegotiationResult {
  negotiationId: string;
  status: NegotiationStatus;
  message: BilingualText;
  allocatedResources?: ResourceAmount;
  alternatives?: ProactiveSuggestion[];
}

export interface ProactiveInteractionRecord {
  type: 'suggestion' | 'negotiation';
  id: string;
  content?: BilingualText;
  resourceType?: ResourceType;
  requestedAmount?: ResourceAmount;
  userAction: SuggestionAction;
  finalAmount?: ResourceAmount;
  timestamp: string;
}

export interface ProactiveHistoryResponse {
  sessionId: string;
  records: ProactiveInteractionRecord[];
  total: number;
}
