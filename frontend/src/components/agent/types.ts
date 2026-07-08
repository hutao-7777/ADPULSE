export interface DSPStatus {
  name: string;
  budget_remaining: number;
  target_segments: string[];
  max_cpm: number;
  pacing_rate: number;
  bidding_strategy: string;
}

export interface PerformanceMetrics {
  impressions: number;
  clicks: number;
  ctr: number;
  spend: number;
  revenue: number;
  roi: number;
  spend_ratio: number;
  budget?: number;
  days?: number;
}

export interface ThoughtData {
  performance: PerformanceMetrics;
  benchmark: {
    avg_cpm: number;
    avg_ctr: number;
    competition_level: string;
  };
  derived: {
    win_rate: number;
    avg_winning_cpm: number;
    auction_count: number;
  };
  creative?: {
    exists?: boolean;
    name?: string;
    ai_score?: number;
    fatigue_score?: number;
    ctr?: number;
  };
}

export interface ThoughtStep {
  analysis: string;
  data: ThoughtData;
}

export interface ActionStep {
  action: string;
  parameters: Record<string, unknown>;
  reasoning: string;
}

export interface ObservationStep {
  observation: string;
  expected_vs_actual: Record<string, number>;
  learned: string;
}

export interface AgentIteration {
  iteration: number;
  thought: ThoughtStep;
  action: ActionStep;
  observation: ObservationStep;
}

export interface AgentRunResponse {
  campaign_id: string;
  iterations: AgentIteration[];
  final_recommendation: string;
  metrics_before: PerformanceMetrics;
  metrics_after: PerformanceMetrics;
}

export interface AgentMemoryEntry {
  timestamp: string;
  action: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  expected_vs_actual: Record<string, number>;
  learned: string;
}

export interface AgentMemoryResponse {
  campaign_id: string;
  memory: AgentMemoryEntry[];
}

export interface AgentStatus {
  campaign_id: string;
  strategy: {
    target_cpa: number;
    max_cpm: number;
    daily_budget: number;
  };
  memory_size: number;
  current_state: string;
  last_action: string | null;
}

export interface StepDurations {
  think: number;
  act: number;
  observe: number;
}
