export interface JourneyStep {
  seq: number;
  channel: string;
  event_type: string;
  event_time: string;
  credits?: Record<string, number>;
}

export interface AttributionResult {
  journey: JourneyStep[];
  conversion_value: number;
  models: Record<string, Record<string, number>>;
  model_credits: Record<string, Record<string, number>>;
  summary: string;
}

export interface ModelComparison {
  model_type: string;
  channel_credits: { channel: string; avg_credit: number }[];
}

export interface TrafficQuality {
  quality_score: number;
  grade: 'premium' | 'standard' | 'low' | 'fraud';
  ctr_score: number;
  cvr_score: number;
  bounce_score: number;
  dwell_score: number;
  interaction_score: number;
  flags: string[];
  anomaly_count: number;
  metrics?: Record<string, number>;
}

export interface FraudAlert {
  id: string;
  campaign_id: string;
  alert_type: string;
  severity: 'warning' | 'critical';
  description: string;
  detected_at: string;
  status: 'open' | 'resolved' | 'ignored';
}
