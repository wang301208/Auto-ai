export interface ThoughtNode {
  id: string;
  level: number;
  description: string;
  status: string;
  confidence: number;
  children: ThoughtNode[];
  start_time?: number;
  end_time?: number;
}

export interface ThoughtChain {
  root: ThoughtNode;
}

export interface EmotionEvent {
  type: string;
  intensity: number;
  trigger_reason?: string;
  timestamp: string;
  emoji?: string;
}

export interface AutonomousInitiative {
  action_type: 'suggest' | 'warn' | 'share' | 'request';
  message: string;
  priority: number;
  requires_approval: boolean;
  timestamp: string;
}

export interface InitiativeEvent {
  type: 'radical.initiative';
  desire_type: string;
  urgency: number;
  initiative: AutonomousInitiative;
}
