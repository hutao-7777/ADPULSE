export const CAMPAIGNS = [
  { id: '1cd5fe53-5679-59a4-8e7f-b6653a587b95', name: 'Summer Sale 2026' },
  { id: '5d6ae7a9-d29d-52c2-9a5b-26935a98c82a', name: 'App Install Q3' },
  { id: '2a7c27d8-efd0-5861-88f5-8a646cad71a9', name: 'Brand Awareness' },
];

export const MODELS = ['first_touch', 'last_touch', 'linear', 'time_decay', 'position_based', 'shapley'];

export const MODEL_LABELS: Record<string, string> = {
  first_touch: '首次触点',
  last_touch: '末次触点',
  linear: '线性',
  time_decay: '时间衰减',
  position_based: 'U型位置',
  shapley: 'Shapley近似',
};

export const CHANNEL_COLORS: Record<string, string> = {
  display_view: '#3B82F6',
  display_click: '#2563EB',
  search: '#10B981',
  social: '#A855F7',
  direct: '#64748B',
};

export const GRADE_COLORS: Record<string, string> = {
  premium: 'text-success',
  standard: 'text-accent',
  low: 'text-warning',
  fraud: 'text-danger',
};

export const GRADE_BG: Record<string, string> = {
  premium: 'bg-success/10 border-success/30',
  standard: 'bg-accent/10 border-accent/30',
  low: 'bg-warning/10 border-warning/30',
  fraud: 'bg-danger/10 border-danger/30',
};

export const GRADE_LABELS: Record<string, string> = {
  premium: 'Premium',
  standard: 'Standard',
  low: 'Low Quality',
  fraud: 'Fraud',
};

export const SUB_LABELS: Record<string, string> = {
  ctr_score: 'CTR 合理性',
  cvr_score: 'CVR 合理性',
  bounce_score: '跳出率',
  dwell_score: '停留时长',
  interaction_score: '互动深度',
};

export function channelColor(channel: string): string {
  return CHANNEL_COLORS[channel] || '#94A3B8';
}

export function channelLabel(channel: string): string {
  const map: Record<string, string> = {
    display_view: '展示曝光',
    display_click: '展示点击',
    search: '搜索',
    social: '社交',
    direct: '直接访问',
  };
  return map[channel] || channel;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function flagLabel(flag: string): string {
  const map: Record<string, string> = {
    suspect_bot: '疑似机器人',
    low_quality_ip: '低质量IP',
    ctr_anomaly: 'CTR异常',
    bot_suspect: '疑似作弊',
    night_spike: '夜间流量激增',
    overall_fraud_score: '综合质量过低',
  };
  return map[flag] || flag;
}
