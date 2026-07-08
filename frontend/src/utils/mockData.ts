/**
 * Frontend mock data for offline development and UI component testing.
 *
 * These objects mirror the shapes returned by the AdPulse backend APIs.
 * Chart components can import from here when the backend is not available.
 */

export const mockKPIs = {
  totalSpend: 13550,
  totalImpressions: 1_245_000,
  totalClicks: 31_250,
  ctr: 0.0251,
  conversions: 2_890,
  revenue: 98_420,
  roi: 7.26,
  avgCpm: 10.88,
  winRate: 0.34,
};

export const mockRTBTrend = Array.from({ length: 24 }).map((_, i) => {
  const hour = i.toString().padStart(2, '0') + ':00';
  return {
    time: hour,
    winRate: 0.22 + Math.random() * 0.18,
    avgBid: 5.0 + Math.random() * 6.0,
    impressions: Math.floor(2000 + Math.random() * 8000),
    clicks: Math.floor(50 + Math.random() * 300),
  };
});

export const mockDSPBudgets = [
  { name: 'DSP_A', budget: 5000, spent: 3120, remaining: 1880, winRate: 0.38 },
  { name: 'DSP_B', budget: 8000, spent: 5210, remaining: 2790, winRate: 0.31 },
  { name: 'DSP_C', budget: 6000, spent: 1800, remaining: 4200, winRate: 0.25 },
];

export const mockCreativeScores = [
  {
    id: 'seed-creative-1',
    name: 'summer_banner_v1',
    aiScore: 87,
    predictedCtr: 0.032,
    fatigueScore: 0.25,
    imagePath: 'uploads/seed_summer_banner_v1.png',
  },
  {
    id: 'seed-creative-2',
    name: 'summer_banner_v2',
    aiScore: 72,
    predictedCtr: 0.025,
    fatigueScore: 0.45,
    imagePath: 'uploads/seed_summer_banner_v2.png',
  },
  {
    id: 'seed-creative-3',
    name: 'app_install_native',
    aiScore: 91,
    predictedCtr: 0.041,
    fatigueScore: 0.15,
    imagePath: 'uploads/seed_app_install_native.png',
  },
];

export const mockABTests = [
  {
    id: 'seed-abtest-1',
    name: 'Summer Banner Test',
    status: 'running',
    metricTarget: 'ctr',
    trafficSplit: 0.5,
    daysRunning: 3,
    winner: 'blue_cta',
    variants: [
      {
        name: 'control',
        trafficPct: 0.5,
        impressions: 2500,
        clicks: 75,
        conversions: 5,
        revenue: 250,
        ctr: 0.03,
        conversionRate: 0.0667,
        liftPct: 0,
        pValue: 1.0,
        isSignificant: false,
      },
      {
        name: 'blue_cta',
        trafficPct: 0.5,
        impressions: 2480,
        clicks: 92,
        conversions: 7,
        revenue: 420,
        ctr: 0.0371,
        conversionRate: 0.0761,
        liftPct: 23.7,
        pValue: 0.0412,
        isSignificant: true,
      },
    ],
  },
  {
    id: 'seed-abtest-2',
    name: 'Landing Page Test',
    status: 'stopped',
    metricTarget: 'conversion_rate',
    trafficSplit: 0.5,
    daysRunning: 4,
    winner: 'simplified',
    variants: [
      {
        name: 'original',
        trafficPct: 0.5,
        impressions: 1200,
        clicks: 48,
        conversions: 5,
        revenue: 180,
        ctr: 0.04,
        conversionRate: 0.1042,
        liftPct: 0,
        pValue: 1.0,
        isSignificant: false,
      },
      {
        name: 'simplified',
        trafficPct: 0.5,
        impressions: 1180,
        clicks: 52,
        conversions: 8,
        revenue: 320,
        ctr: 0.0441,
        conversionRate: 0.1538,
        liftPct: 47.6,
        pValue: 0.0321,
        isSignificant: true,
      },
    ],
  },
];

export const mockAgentDecision = {
  campaignId: 'seed-campaign-1',
  finalRecommendation: 'blue_cta 显著优于 control (p=0.0412)',
  metricsBefore: {
    impressions: 125000,
    clicks: 3125,
    ctr: 0.025,
    spend: 1355.0,
    revenue: 9842.0,
    roi: 7.26,
    spendRatio: 0.27,
  },
  metricsAfter: {
    impressions: 138000,
    clicks: 3720,
    ctr: 0.027,
    spend: 1480.0,
    revenue: 11200.0,
    roi: 7.57,
    spendRatio: 0.3,
  },
  iterations: [
    {
      iteration: 1,
      thought: {
        analysis:
          'Campaign seed-campaign-1 过去7天获得 125000 次展示, 3125 次点击, CTR 0.0250. 总花费 ¥1355.00, 收入 ¥9842.00, ROI 7.26, 预算消耗率 27.0%. 市场基准 CTR 0.0236, 平均CPM ¥10.88, 竞争强度 medium. 当前各项指标处于正常区间。',
        data: {
          performance: {
            impressions: 125000,
            clicks: 3125,
            ctr: 0.025,
            spend: 1355.0,
            revenue: 9842.0,
            roi: 7.26,
            spendRatio: 0.27,
          },
          benchmark: { avgCpm: 10.88, avgCtr: 0.0236, competitionLevel: 'medium' },
          derived: { winRate: 0.34, avgWinningCpm: 9.2, auctionCount: 120 },
        },
      },
      action: {
        action: 'increase_bid',
        parameters: { bid_adjustment_pct: 0.15 },
        reasoning:
          'ROI 7.26 大于2.0, 广告效益良好, 建议适度加大投入以获取更多优质流量。',
      },
      observation: {
        observation:
          '执行 increase_bid 后, 预估 impressions 变化 22.5%, 实际预估反馈 24.1%; CTR 预估变化 -1.5%。',
        expectedVsActual: {
          expectedCtrChangePct: -1.5,
          actualCtrChangePct: -1.48,
          expectedImpressionsChangePct: 22.5,
          actualImpressionsChangePct: 24.1,
        },
        learned: '出价提升带来了更多曝光机会, 但需关注 ROI 是否同步改善。',
      },
    },
    {
      iteration: 2,
      thought: {
        analysis:
          '出价调整后 Campaign 获得 138000 次展示, CTR 0.0270, 收入提升至 ¥11200.00, ROI 7.57. 指标继续改善。',
        data: {
          performance: {
            impressions: 138000,
            clicks: 3720,
            ctr: 0.027,
            spend: 1480.0,
            revenue: 11200.0,
            roi: 7.57,
            spendRatio: 0.3,
          },
          benchmark: { avgCpm: 10.88, avgCtr: 0.0236, competitionLevel: 'medium' },
          derived: { winRate: 0.37, avgWinningCpm: 9.85, auctionCount: 135 },
        },
      },
      action: {
        action: 'maintain_strategy',
        parameters: {},
        reasoning: '当前各项指标处于健康区间, 建议保持当前策略继续观察。',
      },
      observation: {
        observation: '保持当前策略, 持续监控核心指标变化。',
        expectedVsActual: {},
        learned: '指标健康时避免频繁调整, 让模型/数据稳定积累。',
      },
    },
  ],
};

export const mockAttributionJourney = [
  { seq: 1, channel: 'display_view', event_type: 'impression', event_time: '2026-07-01T10:00:00', credits: {} as Record<string, number> },
  { seq: 2, channel: 'search', event_type: 'impression', event_time: '2026-07-02T14:30:00', credits: {} as Record<string, number> },
  { seq: 3, channel: 'display_click', event_type: 'click', event_time: '2026-07-03T09:15:00', credits: {} as Record<string, number> },
  { seq: 4, channel: 'social', event_type: 'click', event_time: '2026-07-05T16:45:00', credits: {} as Record<string, number> },
  { seq: 5, channel: 'direct', event_type: 'conversion', event_time: '2026-07-06T11:20:00', credits: {} as Record<string, number> },
];

export const mockAttributionCredits: Record<string, Record<string, number>> = {
  first_touch: { display_view: 1.0 },
  last_touch: { direct: 1.0 },
  linear: { display_view: 0.2, search: 0.2, display_click: 0.2, social: 0.2, direct: 0.2 },
  time_decay: { display_view: 0.06, search: 0.11, display_click: 0.22, social: 0.28, direct: 0.33 },
  position_based: { display_view: 0.4, search: 0.067, display_click: 0.066, social: 0.067, direct: 0.4 },
  shapley: { display_view: 0.32, search: 0.18, display_click: 0.22, social: 0.16, direct: 0.12 },
};

export const mockAttribution = {
  journey: mockAttributionJourney,
  conversion_value: 1000,
  models: Object.fromEntries(
    Object.entries(mockAttributionCredits).map(([model, credits]) => [
      model,
      Object.fromEntries(Object.entries(credits).map(([ch, c]) => [ch, Math.round(c * 1000)])),
    ])
  ),
  model_credits: mockAttributionCredits,
  summary:
    '用户旅程包含 5 个触点，涉及渠道: display_view, search, display_click, social, direct。首次触点 display_view，末次触点 direct。首次触点模型下 display_view 贡献最高，末次触点模型下 direct 贡献最高。',
};

export const mockTrafficQuality = {
  quality_score: 72,
  grade: 'standard',
  ctr_score: 78,
  cvr_score: 82,
  bounce_score: 65,
  dwell_score: 70,
  interaction_score: 75,
  flags: ['night_spike'],
  anomaly_count: 1,
  metrics: {
    ctr: 0.025,
    cvr: 0.08,
    bounce_rate: 0.55,
    avg_dwell_sec: 18,
    interaction_rate: 0.18,
  },
};

export const mockFraudAlerts = [
  {
    id: 'alert-1',
    campaign_id: 'seed-campaign-1',
    alert_type: 'night_spike',
    severity: 'warning',
    description: '夜间(0-6点)流量占比超过50%，存在非人类流量特征。',
    detected_at: '2026-07-08T03:20:00',
    status: 'open',
  },
  {
    id: 'alert-2',
    campaign_id: 'seed-campaign-1',
    alert_type: 'suspect_bot',
    severity: 'critical',
    description: '同一用户在1分钟内点击超过3次，疑似机器人刷量。',
    detected_at: '2026-07-08T02:15:00',
    status: 'open',
  },
];

const mockData = {
  kpis: mockKPIs,
  rtbTrend: mockRTBTrend,
  dspBudgets: mockDSPBudgets,
  creativeScores: mockCreativeScores,
  abTests: mockABTests,
  agentDecision: mockAgentDecision,
  attribution: mockAttribution,
  trafficQuality: mockTrafficQuality,
  fraudAlerts: mockFraudAlerts,
};

export default mockData;
