export interface ABTest {
  id: string;
  name: string;
  campaign_id: string;
  status: 'draft' | 'running' | 'stopped' | 'completed';
  traffic_split: number;
  metric_target: 'ctr' | 'conversion_rate' | 'roi';
  start_date: string | null;
  end_date: string | null;
  winner: string | null;
  created_at: string;
}

export interface VariantStat {
  name: string;
  traffic_pct: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
  ctr: number;
  conversion_rate: number;
  roi: number;
  lift_pct: number;
  p_value: number;
  is_significant: boolean;
  sample_size_reached: boolean;
  confidence_interval: [number, number];
  power: number;
}

export interface TestInfo {
  name: string;
  status: string;
  metric_target: string;
  start_date: string | null;
  days_running: number;
}

export interface TestResults {
  test_info: TestInfo;
  variants: VariantStat[];
  recommendation: string;
}

export interface AnomalyAlert {
  variant: string;
  metric: string;
  current_value: number;
  expected_range: [number, number];
  severity: 'warning' | 'critical';
}

export interface CampaignOption {
  id: string;
  name: string;
}
