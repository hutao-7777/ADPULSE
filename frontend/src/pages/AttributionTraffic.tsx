import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
  User,
} from 'lucide-react';

import { apiRequest } from '../utils/api';
import {
  mockAttribution,
  mockTrafficQuality,
  mockFraudAlerts,
} from '../utils/mockData';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface JourneyStep {
  seq: number;
  channel: string;
  event_type: string;
  event_time: string;
  credits?: Record<string, number>;
}

interface AttributionResult {
  journey: JourneyStep[];
  conversion_value: number;
  models: Record<string, Record<string, number>>;
  model_credits: Record<string, Record<string, number>>;
  summary: string;
}

interface ModelComparison {
  model_type: string;
  channel_credits: { channel: string; avg_credit: number }[];
}

interface TrafficQuality {
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

interface FraudAlert {
  id: string;
  campaign_id: string;
  alert_type: string;
  severity: 'warning' | 'critical';
  description: string;
  detected_at: string;
  status: 'open' | 'resolved' | 'ignored';
}

// ------------------------------------------------------------------
// 常量
// ------------------------------------------------------------------

const CAMPAIGNS = [
  { id: '1cd5fe53-5679-59a4-8e7f-b6653a587b95', name: 'Summer Sale 2026' },
  { id: '5d6ae7a9-d29d-52c2-9a5b-26935a98c82a', name: 'App Install Q3' },
  { id: '2a7c27d8-efd0-5861-88f5-8a646cad71a9', name: 'Brand Awareness' },
];

const MODELS = ['first_touch', 'last_touch', 'linear', 'time_decay', 'position_based', 'shapley'];

const MODEL_LABELS: Record<string, string> = {
  first_touch: '首次触点',
  last_touch: '末次触点',
  linear: '线性',
  time_decay: '时间衰减',
  position_based: 'U型位置',
  shapley: 'Shapley近似',
};

const CHANNEL_COLORS: Record<string, string> = {
  display_view: '#3B82F6',
  display_click: '#2563EB',
  search: '#10B981',
  social: '#A855F7',
  direct: '#64748B',
};

const GRADE_COLORS: Record<string, string> = {
  premium: 'text-success',
  standard: 'text-accent',
  low: 'text-warning',
  fraud: 'text-danger',
};

const GRADE_BG: Record<string, string> = {
  premium: 'bg-success/10 border-success/30',
  standard: 'bg-accent/10 border-accent/30',
  low: 'bg-warning/10 border-warning/30',
  fraud: 'bg-danger/10 border-danger/30',
};

const GRADE_LABELS: Record<string, string> = {
  premium: 'Premium',
  standard: 'Standard',
  low: 'Low Quality',
  fraud: 'Fraud',
};

const SUB_LABELS: Record<string, string> = {
  ctr_score: 'CTR 合理性',
  cvr_score: 'CVR 合理性',
  bounce_score: '跳出率',
  dwell_score: '停留时长',
  interaction_score: '互动深度',
};

// ------------------------------------------------------------------
// 工具函数
// ------------------------------------------------------------------

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

function channelColor(channel: string): string {
  return CHANNEL_COLORS[channel] || '#94A3B8';
}

function channelLabel(channel: string): string {
  const map: Record<string, string> = {
    display_view: '展示曝光',
    display_click: '展示点击',
    search: '搜索',
    social: '社交',
    direct: '直接访问',
  };
  return map[channel] || channel;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function flagLabel(flag: string): string {
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

// ------------------------------------------------------------------
// UserJourneyTimeline 用户旅程时间线
// ------------------------------------------------------------------

interface UserJourneyTimelineProps {
  journey: JourneyStep[];
  credits: Record<string, number>;
  conversionValue: number;
}

function UserJourneyTimeline({ journey, credits, conversionValue }: UserJourneyTimelineProps) {
  const maxCredit = useMemo(() => {
    const vals = Object.values(credits || {});
    return vals.length ? Math.max(...vals) : 1;
  }, [credits]);

  return (
    <div className="card p-5 h-full">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">用户旅程</h3>
      </div>

      {journey.length === 0 ? (
        <p className="text-muted text-sm">暂无触点数据</p>
      ) : (
        <div className="relative flex items-center justify-between py-8 overflow-x-auto">
          {journey.map((step, idx) => {
            const credit = credits?.[step.channel] || 0;
            const size = 24 + Math.max(8, (credit / maxCredit) * 40);
            const isLast = idx === journey.length - 1;
            return (
              <div key={step.seq} className="flex items-center flex-1 min-w-[120px]">
                <div className="flex flex-col items-center group relative">
                  <div
                    className="rounded-full flex items-center justify-center border-2 border-slate-700 shadow-lg transition-transform group-hover:scale-110"
                    style={{
                      width: size,
                      height: size,
                      backgroundColor: channelColor(step.channel),
                    }}
                    title={`${channelLabel(step.channel)} ${step.event_type}\n时间: ${formatTime(step.event_time)}\n功劳值: ${(credit * 100).toFixed(1)}%`}
                  >
                    <span className="text-white text-[10px] font-bold">{step.seq}</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-300 text-center line-clamp-1">
                    {channelLabel(step.channel)}
                  </p>
                  <p className="text-[10px] text-muted">{(credit * 100).toFixed(1)}%</p>

                  {/* Hover tooltip */}
                  <div className="absolute bottom-full mb-2 hidden group-hover:block z-10 w-40 bg-slate-900 border border-slate-700 rounded-lg p-2 shadow-xl">
                    <p className="text-xs text-slate-100 font-medium">{channelLabel(step.channel)}</p>
                    <p className="text-[10px] text-muted">{step.event_type}</p>
                    <p className="text-[10px] text-muted">{formatTime(step.event_time)}</p>
                    <p className="text-[10px] text-accent mt-1">
                      功劳: ¥{(credit * conversionValue).toFixed(2)}
                    </p>
                  </div>
                </div>
                {!isLast && (
                  <div className="flex-1 h-0.5 bg-slate-700 mx-2 relative">
                    <div className="absolute right-0 -top-1 text-slate-600">
                      <ArrowRight size={14} />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// AttributionModelTabs 归因模型切换Tab
// ------------------------------------------------------------------

interface AttributionModelTabsProps {
  activeModel: string;
  onChange: (model: string) => void;
}

function AttributionModelTabs({ activeModel, onChange }: AttributionModelTabsProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {MODELS.map((model) => (
        <button
          key={model}
          onClick={() => onChange(model)}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
            activeModel === model
              ? 'bg-accent/15 text-accent border-accent/50'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-600'
          )}
        >
          {MODEL_LABELS[model]}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------
// ModelComparisonTable 模型对比表格
// ------------------------------------------------------------------

interface ModelComparisonTableProps {
  modelCredits: Record<string, Record<string, number>>;
}

function ModelComparisonTable({ modelCredits }: ModelComparisonTableProps) {
  const channels = useMemo(() => {
    const set = new Set<string>();
    Object.values(modelCredits).forEach((credits) => Object.keys(credits).forEach((ch) => set.add(ch)));
    return Array.from(set);
  }, [modelCredits]);

  return (
    <div className="card p-5 h-full overflow-auto">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">模型对比</h3>
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-muted border-b border-slate-700">
            <th className="pb-2 font-medium">渠道</th>
            {MODELS.map((model) => (
              <th key={model} className="pb-2 font-medium text-right">
                {MODEL_LABELS[model]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {channels.map((channel) => (
            <tr key={channel} className="border-b border-slate-800/50 last:border-0">
              <td className="py-2 text-slate-200">
                <span
                  className="inline-block w-2 h-2 rounded-full mr-2"
                  style={{ backgroundColor: channelColor(channel) }}
                />
                {channelLabel(channel)}
              </td>
              {MODELS.map((model) => {
                const value = modelCredits[model]?.[channel] || 0;
                return (
                  <td key={model} className="py-2 text-right">
                    <span
                      className="px-2 py-0.5 rounded font-mono"
                      style={{
                        backgroundColor: `rgba(59, 130, 246, ${value * 0.6})`,
                      }}
                    >
                      {(value * 100).toFixed(1)}%
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
          <tr className="font-semibold text-slate-100">
            <td className="py-2">Total</td>
            {MODELS.map((model) => {
              const total = Object.values(modelCredits[model] || {}).reduce((a, b) => a + b, 0);
              return (
                <td key={model} className="py-2 text-right font-mono">
                  {(total * 100).toFixed(1)}%
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
// QualityScoreGauge 质量评分仪表盘
// ------------------------------------------------------------------

interface QualityScoreGaugeProps {
  quality: TrafficQuality;
}

function QualityScoreGauge({ quality }: QualityScoreGaugeProps) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference * (1 - quality.quality_score / 100);

  return (
    <div className="card p-5 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">流量质量评分</h3>
      </div>

      <div className="flex flex-col items-center">
        <div className="relative w-40 h-40">
          <svg width="160" height="160" viewBox="0 0 100 100" className="-rotate-90">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#334155" strokeWidth="8" />
            <circle
              cx="50"
              cy="50"
              r="45"
              fill="none"
              stroke={quality.quality_score >= 90 ? '#10B981' : quality.quality_score >= 70 ? '#3B82F6' : quality.quality_score >= 50 ? '#F59E0B' : '#EF4444'}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="transition-all duration-700"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={cn('text-4xl font-bold font-mono', GRADE_COLORS[quality.grade])}>
              {quality.quality_score}
            </span>
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full border mt-1', GRADE_BG[quality.grade], GRADE_COLORS[quality.grade])}>
              {GRADE_LABELS[quality.grade]}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// SubDimensionBars 子维度进度条
// ------------------------------------------------------------------

interface SubDimensionBarsProps {
  quality: TrafficQuality;
}

function SubDimensionBars({ quality }: SubDimensionBarsProps) {
  const dims = [
    { key: 'ctr_score', score: quality.ctr_score },
    { key: 'cvr_score', score: quality.cvr_score },
    { key: 'bounce_score', score: quality.bounce_score },
    { key: 'dwell_score', score: quality.dwell_score },
    { key: 'interaction_score', score: quality.interaction_score },
  ];

  return (
    <div className="card p-5 h-full">
      <h3 className="text-base font-semibold text-slate-100 mb-4">子维度评分</h3>
      <div className="space-y-3">
        {dims.map(({ key, score }) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">{SUB_LABELS[key]}</span>
              <span className="font-mono text-slate-200">{score}</span>
            </div>
            <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  score >= 80 ? 'bg-success' : score >= 60 ? 'bg-accent' : score >= 50 ? 'bg-warning' : 'bg-danger'
                )}
                style={{ width: `${score}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// FraudAlertList 作弊告警列表
// ------------------------------------------------------------------

interface FraudAlertListProps {
  alerts: FraudAlert[];
  onResolve?: (id: string) => void;
}

function FraudAlertList({ alerts, onResolve }: FraudAlertListProps) {
  const sorted = useMemo(
    () => [...alerts].sort((a) => (a.severity === 'critical' ? -1 : 1)),
    [alerts]
  );

  return (
    <div className="card p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert size={18} className="text-danger" />
        <h3 className="text-base font-semibold text-slate-100">作弊告警</h3>
        <span className="ml-auto text-xs text-muted">{alerts.length} 条</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {sorted.length === 0 && (
          <p className="text-center text-muted text-sm py-6">暂无告警</p>
        )}

        {sorted.map((alert) => (
          <div
            key={alert.id}
            className={cn(
              'p-3 rounded-lg border transition-colors',
              alert.severity === 'critical'
                ? 'bg-danger/5 border-danger/30'
                : 'bg-warning/5 border-warning/30',
              alert.status === 'resolved' && 'opacity-50'
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                {alert.severity === 'critical' ? (
                  <AlertTriangle size={16} className="text-danger flex-shrink-0" />
                ) : (
                  <Activity size={16} className="text-warning flex-shrink-0" />
                )}
                <span
                  className={cn(
                    'text-[10px] px-1.5 py-0.5 rounded-full border font-medium',
                    alert.severity === 'critical'
                      ? 'bg-danger/10 text-danger border-danger/30'
                      : 'bg-warning/10 text-warning border-warning/30'
                  )}
                >
                  {alert.severity === 'critical' ? 'Critical' : 'Warning'}
                </span>
              </div>
              {alert.status === 'open' && onResolve && (
                <button
                  onClick={() => onResolve(alert.id)}
                  className="text-[10px] text-success hover:text-green-400 flex items-center gap-0.5"
                >
                  <CheckCircle2 size={10} />
                  解决
                </button>
              )}
            </div>
            <p className="mt-2 text-sm text-slate-200">{flagLabel(alert.alert_type)}</p>
            <p className="text-xs text-muted mt-1">{alert.description}</p>
            <p className="text-[10px] text-slate-500 mt-2">
              {new Date(alert.detected_at).toLocaleString('zh-CN')}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// AttributionTraffic 主页面
// ------------------------------------------------------------------

function AttributionTraffic() {
  const [selectedCampaignId, setSelectedCampaignId] = useState(CAMPAIGNS[0].id);
  const [userId, setUserId] = useState('demo-user-001');
  const [activeModel, setActiveModel] = useState('first_touch');
  const [attribution, setAttribution] = useState<AttributionResult | null>(null);
  const [, setModelComparison] = useState<ModelComparison[]>([]);
  const [quality, setQuality] = useState<TrafficQuality>(mockTrafficQuality as TrafficQuality);
  const [alerts, setAlerts] = useState<FraudAlert[]>(mockFraudAlerts as FraudAlert[]);
  const [loadingAttribution, setLoadingAttribution] = useState(false);
  const [loadingTraffic, setLoadingTraffic] = useState(false);

  useEffect(() => {
    loadMockData();
  }, []);

  const loadMockData = () => {
    setAttribution(mockAttribution);
    setActiveModel('first_touch');
    setModelComparison(
      MODELS.map((model) => ({
        model_type: model,
        channel_credits: Object.entries(mockAttribution.model_credits[model] || {}).map(
          ([channel, avg_credit]) => ({ channel, avg_credit })
        ),
      }))
    );
    setQuality(mockTrafficQuality as TrafficQuality);
    setAlerts(mockFraudAlerts as FraudAlert[]);
  };

  const initSampleJourney = async () => {
    setLoadingAttribution(true);
    try {
      const baseTime = new Date();
      const touchpoints: { channel: string; event_type: string; offsetHours: number }[] = [
        { channel: 'display_view', event_type: 'impression', offsetHours: -96 },
        { channel: 'search', event_type: 'impression', offsetHours: -72 },
        { channel: 'display_click', event_type: 'click', offsetHours: -48 },
        { channel: 'social', event_type: 'click', offsetHours: -24 },
      ];

      for (const tp of touchpoints) {
        const eventTime = new Date(baseTime.getTime() + tp.offsetHours * 3600000).toISOString();
        await apiRequest('/attribution/journey', {
          method: 'POST',
          body: JSON.stringify({
            user_id: userId,
            campaign_id: selectedCampaignId,
            channel: tp.channel,
            event_type: tp.event_type,
            event_time: eventTime,
          }),
        });
      }

      await apiRequest('/attribution/conversion', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          campaign_id: selectedCampaignId,
          conversion_value: 1000,
          channel: 'direct',
        }),
      });

      const calc = await apiRequest<AttributionResult>(
        `/attribution/calculate/${userId}/${selectedCampaignId}`,
        {
          method: 'POST',
          body: JSON.stringify({ conversion_value: 1000 }),
        }
      );
      setAttribution(calc);

      const comparison = await apiRequest<{ comparisons: ModelComparison[] }>('/attribution/model-comparison');
      setModelComparison(comparison.comparisons);
    } catch (err) {
      console.error('归因分析失败:', err);
      alert('后端归因调用失败，已回退到模拟数据');
      loadMockData();
    } finally {
      setLoadingAttribution(false);
    }
  };

  const assessTraffic = async () => {
    setLoadingTraffic(true);
    try {
      const rawMetrics = {
        impressions: 12000,
        clicks: 300,
        conversions: 24,
        bounce_count: 90,
        total_dwell_sec: 4800,
        interaction_events: 2100,
        unique_users: 280,
        click_timestamps: [1, 2, 3, 4, 5],
        ip_distribution: { '192.168.1.1': 150 },
      };

      const score = await apiRequest<TrafficQuality>('/traffic/assess', {
        method: 'POST',
        body: JSON.stringify({
          campaign_id: selectedCampaignId,
          raw_metrics: rawMetrics,
        }),
      });
      setQuality(score);

      const alertsData = await apiRequest<FraudAlert[]>(`/traffic/alerts/${selectedCampaignId}`);
      setAlerts(alertsData);
    } catch (err) {
      console.error('流量评估失败:', err);
      alert('后端流量评估失败，已回退到模拟数据');
      setQuality(mockTrafficQuality as TrafficQuality);
      setAlerts(mockFraudAlerts as FraudAlert[]);
    } finally {
      setLoadingTraffic(false);
    }
  };

  const resolveAlert = async (alertId: string) => {
    try {
      await apiRequest(`/traffic/alerts/${alertId}/resolve`, { method: 'POST' });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: 'resolved' } : a))
      );
    } catch (err) {
      console.error('解决告警失败:', err);
    }
  };

  const activeCredits = attribution?.model_credits?.[activeModel] || {};

  return (
    <div className="space-y-4 pb-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">归因分析 & 流量质量</h1>
        <p className="text-muted mt-1">多触点归因模型对比与实时流量质量监测</p>
      </header>

      {/* 控制面板 */}
      <div className="card p-4 flex flex-col lg:flex-row items-end gap-4">
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1.5">Campaign</label>
          <select
            value={selectedCampaignId}
            onChange={(e) => setSelectedCampaignId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            {CAMPAIGNS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-muted mb-1.5 flex items-center gap-1">
            <User size={12} />
            用户 ID
          </label>
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          />
        </div>
        <button
          onClick={initSampleJourney}
          disabled={loadingAttribution}
          className="btn-primary flex items-center gap-2 text-sm disabled:opacity-60"
        >
          {loadingAttribution ? <RefreshCw size={14} className="animate-spin" /> : <TrendingUp size={14} />}
          初始化示例并计算归因
        </button>
        <button
          onClick={assessTraffic}
          disabled={loadingTraffic}
          className="btn-secondary flex items-center gap-2 text-sm disabled:opacity-60"
        >
          {loadingTraffic ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
          评估流量质量
        </button>
        <button onClick={loadMockData} className="btn-secondary text-sm">
          模拟数据
        </button>
      </div>

      {/* 归因分析区 */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 space-y-4">
          <AttributionModelTabs activeModel={activeModel} onChange={setActiveModel} />
          <UserJourneyTimeline
            journey={attribution?.journey || []}
            credits={activeCredits}
            conversionValue={attribution?.conversion_value || 0}
          />
          {attribution?.summary && (
            <div className="card p-4 text-sm text-slate-300">{attribution.summary}</div>
          )}
        </div>
        <div className="lg:col-span-2">
          <ModelComparisonTable modelCredits={attribution?.model_credits || mockAttribution.model_credits} />
        </div>
      </div>

      {/* 流量质量区 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <QualityScoreGauge quality={quality} />
        </div>
        <div className="lg:col-span-1">
          <SubDimensionBars quality={quality} />
        </div>
        <div className="lg:col-span-1">
          <FraudAlertList alerts={alerts} onResolve={resolveAlert} />
        </div>
      </div>
    </div>
  );
}

export default AttributionTraffic;
