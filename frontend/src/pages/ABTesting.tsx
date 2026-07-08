import { useEffect, useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Plus,
  Play,
  Square,
  Trash2,
  X,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  Minus,
  Activity,
} from 'lucide-react';

import { apiRequest } from '../utils/api';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface ABTest {
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

interface VariantStat {
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

interface TestInfo {
  name: string;
  status: string;
  metric_target: string;
  start_date: string | null;
  days_running: number;
}

interface TestResults {
  test_info: TestInfo;
  variants: VariantStat[];
  recommendation: string;
}

interface AnomalyAlert {
  variant: string;
  metric: string;
  current_value: number;
  expected_range: [number, number];
  severity: 'warning' | 'critical';
}

interface CampaignOption {
  id: string;
  name: string;
}

// ------------------------------------------------------------------
// 工具函数
// ------------------------------------------------------------------

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function getStatusBadge(status: ABTest['status']) {
  const map: Record<string, { label: string; className: string; pulse?: boolean }> = {
    draft: { label: '草稿', className: 'bg-slate-600/20 text-slate-300 border-slate-500/30' },
    running: { label: '运行中', className: 'bg-success/15 text-success border-success/40', pulse: true },
    stopped: { label: '已停止', className: 'bg-danger/15 text-danger border-danger/40' },
    completed: { label: '已完成', className: 'bg-accent/15 text-accent border-accent/40' },
  };
  return map[status] || map.draft;
}

function metricLabel(metric: string): string {
  const map: Record<string, string> = {
    ctr: 'CTR',
    conversion_rate: 'Conversion Rate',
    roi: 'ROI',
  };
  return map[metric] || metric;
}

function formatMetric(value: number, metric: string): string {
  if (metric === 'ctr' || metric === 'conversion_rate') return `${(value * 100).toFixed(2)}%`;
  if (metric === 'roi') return `${value.toFixed(2)}x`;
  return value.toFixed(2);
}

const MOCK_CAMPAIGNS: CampaignOption[] = [
  { id: '12345678-1234-1234-1234-123456789abc', name: '夏季促销活动' },
  { id: '22345678-1234-1234-1234-123456789abc', name: '品牌认知推广' },
  { id: '32345678-1234-1234-1234-123456789abc', name: '新品首发' },
];

// ------------------------------------------------------------------
// TestList 测试列表
// ------------------------------------------------------------------

interface TestListProps {
  tests: ABTest[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  loading?: boolean;
}

function TestList({ tests, selectedId, onSelect, onNew, loading }: TestListProps) {
  return (
    <div className="card p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-slate-100">测试列表</h2>
        <button onClick={onNew} className="btn-primary flex items-center gap-1.5 text-sm px-3 py-1.5">
          <Plus size={14} />
          新建测试
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {loading && (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-slate-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {!loading && tests.length === 0 && (
          <div className="text-center py-10 text-muted text-sm">暂无 A/B 测试</div>
        )}

        {tests.map((test) => {
          const badge = getStatusBadge(test.status);
          return (
            <button
              key={test.id}
              onClick={() => onSelect(test.id)}
              className={cn(
                'w-full text-left p-4 rounded-xl border transition-all',
                selectedId === test.id
                  ? 'bg-accent/10 border-accent/50'
                  : 'bg-slate-800/30 border-slate-700/30 hover:border-slate-600 hover:bg-slate-800/50'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-slate-100 line-clamp-1">{test.name}</p>
                <span
                  className={cn(
                    'flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium border shrink-0',
                    badge.className
                  )}
                >
                  {badge.pulse && (
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
                    </span>
                  )}
                  {badge.label}
                </span>
              </div>

              <div className="mt-2 flex items-center gap-3 text-xs text-muted">
                <span>目标: {metricLabel(test.metric_target)}</span>
                <span>·</span>
                <span>{test.start_date ? `运行 ${Math.max(0, Math.floor((Date.now() - new Date(test.start_date).getTime()) / 86400000))} 天` : '未开始'}</span>
              </div>

              <div className="mt-2 flex items-center gap-1 text-xs text-accent">
                <span>领先: {test.winner || '-'}</span>
                <ChevronRight size={12} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// VariantComparisonTable Variant对比表
// ------------------------------------------------------------------

interface VariantComparisonTableProps {
  variants: VariantStat[];
}

function VariantComparisonTable({ variants }: VariantComparisonTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted border-b border-slate-700">
            <th className="pb-3 font-medium">Variant</th>
            <th className="pb-3 font-medium">流量占比</th>
            <th className="pb-3 font-medium">曝光量</th>
            <th className="pb-3 font-medium">点击量</th>
            <th className="pb-3 font-medium">CTR</th>
            <th className="pb-3 font-medium">转化率</th>
            <th className="pb-3 font-medium">收入(¥)</th>
            <th className="pb-3 font-medium">相对提升</th>
            <th className="pb-3 font-medium">P 值</th>
            <th className="pb-3 font-medium">显著性</th>
          </tr>
        </thead>
        <tbody>
          {variants.map((variant, idx) => {
            const isControl = variant.name.toLowerCase() === 'control';
            return (
              <tr
                key={variant.name}
                className={cn(
                  'border-b border-slate-800/50 last:border-0 transition-colors hover:bg-slate-700/30',
                  isControl && 'bg-slate-700/20',
                  idx % 2 === 1 && !isControl && 'bg-slate-800/20',
                  variant.is_significant && !isControl && 'bg-success/5'
                )}
              >
                <td className="py-3 px-2 font-medium text-slate-100">
                  <div className="flex items-center gap-2">
                    {isControl && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-600 text-slate-200">
                        Control
                      </span>
                    )}
                    {variant.name}
                  </div>
                </td>
                <td className="py-3 px-2 font-mono text-slate-300">{(variant.traffic_pct * 100).toFixed(0)}%</td>
                <td className="py-3 px-2 font-mono text-slate-300">{variant.impressions.toLocaleString()}</td>
                <td className="py-3 px-2 font-mono text-slate-300">{variant.clicks.toLocaleString()}</td>
                <td className="py-3 px-2 font-mono text-slate-300">{(variant.ctr * 100).toFixed(2)}%</td>
                <td className="py-3 px-2 font-mono text-slate-300">{(variant.conversion_rate * 100).toFixed(2)}%</td>
                <td className="py-3 px-2 font-mono text-slate-300">¥{variant.revenue.toFixed(2)}</td>
                <td className="py-3 px-2">
                  <span
                    className={cn(
                      'flex items-center gap-1 font-medium',
                      variant.is_significant ? 'text-success' : 'text-muted'
                    )}
                  >
                    {variant.is_significant ? '↑' : '→'}
                    {Math.abs(variant.lift_pct).toFixed(1)}%
                  </span>
                </td>
                <td className="py-3 px-2 font-mono text-slate-300">{variant.p_value.toFixed(4)}</td>
                <td className="py-3 px-2">
                  {variant.is_significant ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-success/10 text-success border border-success/30">
                      ✓ Significant
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700/50 text-muted border border-slate-600">
                      ~ Observing
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------
// TrendChart 趋势对比图
// ------------------------------------------------------------------

interface TrendChartProps {
  variants: VariantStat[];
  metric: string;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A855F7'];

function TrendChart({ variants, metric }: TrendChartProps) {
  // 生成模拟趋势数据
  const data = useMemo(() => {
    const days = 14;
    const base = new Date();
    base.setDate(base.getDate() - days);
    return Array.from({ length: days }).map((_, i) => {
      const date = new Date(base);
      date.setDate(date.getDate() + i);
      const label = date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
      const point: Record<string, number | string> = { date: label };
      variants.forEach((v) => {
        const baseValue = metric === 'ctr' ? v.ctr : metric === 'conversion_rate' ? v.conversion_rate : v.roi;
        const noise = (Math.random() - 0.5) * baseValue * 0.4;
        point[v.name] = Math.max(0, baseValue + noise);
      });
      return point;
    });
  }, [variants, metric]);

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">趋势对比</h3>
      </div>
      <div className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" stroke="#64748B" fontSize={12} tickLine={false} />
            <YAxis
              stroke="#64748B"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => (metric === 'roi' ? `${v}x` : `${(v * 100).toFixed(1)}%`)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1E293B',
                border: '1px solid #334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#F1F5F9' }}
              itemStyle={{ color: '#CBD5E1' }}
              formatter={(value: number) =>
                metric === 'roi' ? [`${value.toFixed(2)}x`, ''] : [`${(value * 100).toFixed(2)}%`, '']
              }
            />
            <Legend wrapperStyle={{ paddingTop: '10px' }} />
            {variants.map((v, i) => (
              <Line
                key={v.name}
                type="monotone"
                dataKey={v.name}
                name={v.name}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// CreateTestModal 新建测试弹窗
// ------------------------------------------------------------------

interface CreateTestModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

function CreateTestModal({ open, onClose, onCreated }: CreateTestModalProps) {
  const [name, setName] = useState('');
  const [campaignId, setCampaignId] = useState(MOCK_CAMPAIGNS[0].id);
  const [metric, setMetric] = useState<'ctr' | 'conversion_rate' | 'roi'>('ctr');
  const [trafficSplit, setTrafficSplit] = useState(50);
  const [variants, setVariants] = useState([{ name: 'control', pct: 50 }, { name: 'variant_a', pct: 50 }]);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const addVariant = () => {
    setVariants((prev) => [...prev, { name: `variant_${String.fromCharCode(98 + prev.length - 1)}`, pct: 0 }]);
  };

  const removeVariant = (idx: number) => {
    setVariants((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateVariant = (idx: number, field: 'name' | 'pct', value: string | number) => {
    setVariants((prev) =>
      prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v))
    );
  };

  const totalPct = variants.reduce((sum, v) => sum + v.pct, 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return alert('请输入测试名称');
    if (totalPct !== 100) return alert('Variant 流量占比之和必须等于 100%');

    setSubmitting(true);
    try {
      await apiRequest('/abtests', {
        method: 'POST',
        body: JSON.stringify({
          name,
          campaign_id: campaignId,
          metric_target: metric,
          traffic_split: trafficSplit / 100,
          variants_config: variants.map((v) => ({ name: v.name, traffic_pct: v.pct / 100 })),
        }),
      });
      onCreated();
      onClose();
      setName('');
      setVariants([{ name: 'control', pct: 50 }, { name: 'variant_a', pct: 50 }]);
    } catch (err) {
      alert(err instanceof Error ? err.message : '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="card w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-slate-100">新建 A/B 测试</h2>
          <button onClick={onClose} className="text-muted hover:text-slate-100">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-muted mb-1.5">测试名称</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              placeholder="例如：落地页按钮文案测试"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-muted mb-1.5">关联 Campaign</label>
              <select
                value={campaignId}
                onChange={(e) => setCampaignId(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              >
                {MOCK_CAMPAIGNS.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted mb-1.5">目标指标</label>
              <select
                value={metric}
                onChange={(e) => setMetric(e.target.value as typeof metric)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
              >
                <option value="ctr">CTR</option>
                <option value="conversion_rate">Conversion Rate</option>
                <option value="roi">ROI</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-muted mb-1.5">
              实验流量比例: {trafficSplit}%
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={trafficSplit}
              onChange={(e) => setTrafficSplit(parseInt(e.target.value))}
              className="w-full accent-accent"
            />
            <p className="text-[10px] text-muted mt-1">剩余流量将走 control variant</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs text-muted">Variant 配置</label>
              <button
                type="button"
                onClick={addVariant}
                className="text-xs text-accent hover:text-blue-400 flex items-center gap-1"
              >
                <Plus size={12} /> 添加
              </button>
            </div>
            <div className="space-y-2">
              {variants.map((variant, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    value={variant.name}
                    onChange={(e) => updateVariant(idx, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
                    placeholder="variant name"
                  />
                  <div className="w-24 relative">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={variant.pct}
                      onChange={(e) => updateVariant(idx, 'pct', parseInt(e.target.value) || 0)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent pr-6"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted">%</span>
                  </div>
                  {variants.length > 2 && (
                    <button
                      type="button"
                      onClick={() => removeVariant(idx)}
                      className="p-2 text-muted hover:text-danger"
                    >
                      <Minus size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <p className={cn('text-[10px] mt-1', totalPct === 100 ? 'text-success' : 'text-warning')}>
              流量占比总计: {totalPct}% {totalPct !== 100 && '(需等于 100%)'}
            </p>
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">
              取消
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="btn-primary text-sm flex items-center gap-2 disabled:opacity-60"
            >
              {submitting ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Plus size={14} />}
              创建测试
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// 内部 Loader 组件
function Loader(props: React.SVGProps<SVGSVGElement>) {
  return <Activity {...props} className={cn('animate-spin', props.className)} />;
}

// ------------------------------------------------------------------
// TestDetail 测试详情
// ------------------------------------------------------------------

interface TestDetailProps {
  test: ABTest | null;
  results: TestResults | null;
  anomaly: AnomalyAlert | null;
  loading?: boolean;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
  onRefresh: () => void;
}

function TestDetail({
  test,
  results,
  anomaly,
  loading,
  onStart,
  onStop,
  onDelete,
  onRefresh,
}: TestDetailProps) {
  if (!test) {
    return (
      <div className="card p-10 h-full flex flex-col items-center justify-center text-center min-h-[500px]">
        <Activity size={48} className="text-muted mb-4" />
        <p className="text-muted">选择一个测试查看详情</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card p-10 h-full flex items-center justify-center min-h-[500px]">
        <Loader className="w-8 h-8 text-accent animate-spin" />
      </div>
    );
  }

  const badge = getStatusBadge(test.status);

  const controlVariant = results?.variants.find((v) => v.name.toLowerCase() === 'control');
  const controlMetricValue = controlVariant
    ? test.metric_target === 'ctr'
      ? controlVariant.ctr
      : test.metric_target === 'conversion_rate'
      ? controlVariant.conversion_rate
      : controlVariant.roi
    : 0;

  return (
    <div className="space-y-4">
      {/* 头部 */}
      <div className="card p-5">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-100">{test.name}</h2>
              <span
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
                  badge.className
                )}
              >
                {badge.pulse && (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
                  </span>
                )}
                {badge.label}
              </span>
            </div>
            <p className="text-sm text-muted mt-1">
              目标指标: {metricLabel(test.metric_target)} · 创建于 {formatDate(test.created_at)}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {test.status === 'draft' && (
              <button onClick={onStart} className="btn-primary flex items-center gap-1.5 text-sm">
                <Play size={14} /> 启动测试
              </button>
            )}
            {test.status === 'running' && (
              <button onClick={onStop} className="btn-secondary flex items-center gap-1.5 text-sm">
                <Square size={14} /> 停止测试
              </button>
            )}
            <button
              onClick={onDelete}
              className="btn-secondary flex items-center gap-1.5 text-sm text-danger hover:text-danger border-danger/30"
            >
              <Trash2 size={14} /> 删除
            </button>
            <button onClick={onRefresh} className="btn-secondary text-sm">
              刷新
            </button>
          </div>
        </div>
      </div>

      {results && (
        <>
          {/* Variant 对比表 */}
          <div className="card p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Variant 对比</h3>
            <VariantComparisonTable variants={results.variants} />
          </div>

          {/* 趋势图 */}
          <TrendChart variants={results.variants} metric={test.metric_target} />

          {/* 统计摘要 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {results.variants
              .filter((v) => v.name.toLowerCase() !== 'control')
              .map((variant) => (
                <div key={variant.name} className="card p-5">
                  <h4 className="text-sm font-semibold text-slate-100 mb-3">
                    {variant.name} 统计摘要
                  </h4>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">95% 置信区间</span>
                      <span className="font-mono text-slate-200">
                        {(() => {
                          const metricValue =
                            test.metric_target === 'ctr'
                              ? variant.ctr
                              : test.metric_target === 'conversion_rate'
                              ? variant.conversion_rate
                              : variant.roi;
                          const lower = controlMetricValue + variant.confidence_interval[0];
                          const upper = controlMetricValue + variant.confidence_interval[1];
                          const margin = (upper - lower) / 2;
                          return `${formatMetric(metricValue, test.metric_target)} ± ${formatMetric(margin, test.metric_target)}`;
                        })()}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">统计功效</span>
                      <span
                        className={cn(
                          'font-mono font-medium',
                          variant.power >= 0.8 ? 'text-success' : 'text-warning'
                        )}
                      >
                        {(variant.power * 100).toFixed(0)}%
                        {variant.power >= 0.8 ? ' ✓' : ' ⚠'}
                      </span>
                    </div>
                    <div className="text-xs text-muted">
                      {variant.power >= 0.8
                        ? '样本量充足'
                        : '建议增加样本量以提升统计可信度'}
                    </div>
                  </div>
                </div>
              ))}

            <div className="card p-5 lg:col-span-2">
              <h4 className="text-sm font-semibold text-slate-100 mb-2">推荐结论</h4>
              <p className="text-sm text-slate-300 leading-relaxed">{results.recommendation}</p>
            </div>
          </div>
        </>
      )}

      {/* 异常检测 */}
      {anomaly && (
        <div className="card p-5 border-danger/40 bg-danger/5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={22} className="text-danger flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-danger">异常检测警告</h4>
              <p className="text-sm text-slate-300 mt-1">
                {anomaly.variant} 的 {anomaly.metric === 'ctr' ? 'CTR' : '转化率'} 当前值为{' '}
                {(anomaly.current_value * 100).toFixed(2)}%，超出正常波动范围 [
                {(anomaly.expected_range[0] * 100).toFixed(2)}%,{' '}
                {(anomaly.expected_range[1] * 100).toFixed(2)}%]。
              </p>
              <button className="mt-3 btn-secondary text-sm text-danger border-danger/30">
                暂停测试并检查
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
// ABTesting 主页面
// ------------------------------------------------------------------

function ABTesting() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [results, setResults] = useState<TestResults | null>(null);
  const [anomaly, setAnomaly] = useState<AnomalyAlert | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const selectedTest = tests.find((t) => t.id === selectedId) || null;

  const fetchTests = async () => {
    setLoadingList(true);
    try {
      const data = await apiRequest<ABTest[]>('/abtests');
      setTests(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      console.error('获取测试列表失败:', err);
    } finally {
      setLoadingList(false);
    }
  };

  const fetchDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const [res, alert] = await Promise.all([
        apiRequest<TestResults>(`/abtests/${id}/results`),
        apiRequest<AnomalyAlert | null>(`/abtests/${id}/anomaly`).catch(() => null),
      ]);
      setResults(res);
      setAnomaly(alert);
    } catch (err) {
      console.error('获取测试详情失败:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchTests();
  }, []);

  useEffect(() => {
    if (selectedId) fetchDetail(selectedId);
  }, [selectedId]);

  const handleStart = async () => {
    if (!selectedId) return;
    try {
      await apiRequest(`/abtests/${selectedId}/start`, { method: 'POST' });
      fetchTests();
      fetchDetail(selectedId);
    } catch (err) {
      alert(err instanceof Error ? err.message : '启动失败');
    }
  };

  const handleStop = async () => {
    if (!selectedId) return;
    try {
      await apiRequest(`/abtests/${selectedId}/stop`, { method: 'POST' });
      fetchTests();
      fetchDetail(selectedId);
    } catch (err) {
      alert(err instanceof Error ? err.message : '停止失败');
    }
  };

  const handleDelete = async () => {
    if (!selectedId || !confirm('确定删除该测试？')) return;
    try {
      await apiRequest(`/abtests/${selectedId}`, { method: 'DELETE' });
      setSelectedId(null);
      fetchTests();
      setResults(null);
      setAnomaly(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '删除失败');
    }
  };

  return (
    <div className="h-[calc(100vh-48px)] flex flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-slate-100">A/B 测试</h1>
        <p className="text-muted mt-1">创建实验、分析统计结果并做出数据驱动决策</p>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-10 gap-4 min-h-0">
        <div className="lg:col-span-3 min-h-0">
          <TestList
            tests={tests}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onNew={() => setShowModal(true)}
            loading={loadingList}
          />
        </div>
        <div className="lg:col-span-7 min-h-0 overflow-y-auto pr-1 pb-2">
          <TestDetail
            test={selectedTest}
            results={results}
            anomaly={anomaly}
            loading={loadingDetail}
            onStart={handleStart}
            onStop={handleStop}
            onDelete={handleDelete}
            onRefresh={() => selectedId && fetchDetail(selectedId)}
          />
        </div>
      </div>

      <CreateTestModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreated={() => {
          fetchTests();
        }}
      />
    </div>
  );
}

export default ABTesting;
