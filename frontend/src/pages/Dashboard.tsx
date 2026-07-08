import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ArrowDown, ArrowUp, Activity, TrendingUp } from 'lucide-react';

import { apiRequest } from '../utils/api';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface TrendPoint {
  label: string;
  value: number;
}

interface KPIData {
  label: string;
  value: number;
  unit: string;
  change: number;
  trend: TrendPoint[];
}

interface WinRateTrendPoint {
  label: string;
  auctions: number;
  wins: number;
  win_rate: number;
  avg_cpm: number;
}

interface WinRateTrendResponse {
  period: string;
  data: WinRateTrendPoint[];
}

interface DSPBudget {
  name: string;
  spent_pct: number;
}

interface ScoreDist {
  range: string;
  count: number;
}

interface ABTestItem {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'draft';
  variant_count: number;
  leading_variant: string;
  confidence: number;
}

// ------------------------------------------------------------------
// 模拟数据
// ------------------------------------------------------------------

const mockKPIData: KPIData[] = [
  {
    label: 'eCPM',
    value: 12.58,
    unit: '¥',
    change: 3.24,
    trend: [
      { label: 'T-6', value: 11.2 },
      { label: 'T-5', value: 11.5 },
      { label: 'T-4', value: 11.8 },
      { label: 'T-3', value: 12.1 },
      { label: 'T-2', value: 12.3 },
      { label: 'T-1', value: 12.5 },
      { label: '今日', value: 12.58 },
    ],
  },
  {
    label: 'CTR',
    value: 2.84,
    unit: '%',
    change: -0.72,
    trend: [
      { label: 'T-6', value: 2.9 },
      { label: 'T-5', value: 2.95 },
      { label: 'T-4', value: 2.88 },
      { label: 'T-3', value: 2.92 },
      { label: 'T-2', value: 2.86 },
      { label: 'T-1', value: 2.85 },
      { label: '今日', value: 2.84 },
    ],
  },
  {
    label: 'Fill Rate',
    value: 78.4,
    unit: '%',
    change: 5.18,
    trend: [
      { label: 'T-6', value: 72.0 },
      { label: 'T-5', value: 73.5 },
      { label: 'T-4', value: 74.2 },
      { label: 'T-3', value: 75.8 },
      { label: 'T-2', value: 76.5 },
      { label: 'T-1', value: 77.1 },
      { label: '今日', value: 78.4 },
    ],
  },
  {
    label: 'ROI',
    value: 2.36,
    unit: 'x',
    change: 12.38,
    trend: [
      { label: 'T-6', value: 1.95 },
      { label: 'T-5', value: 2.05 },
      { label: 'T-4', value: 2.12 },
      { label: 'T-3', value: 2.18 },
      { label: 'T-2', value: 2.25 },
      { label: 'T-1', value: 2.3 },
      { label: '今日', value: 2.36 },
    ],
  },
];

const mockDSPBudgets: DSPBudget[] = [
  { name: 'DSP_A', spent_pct: 65 },
  { name: 'DSP_B', spent_pct: 42 },
  { name: 'DSP_C', spent_pct: 88 },
  { name: 'DSP_D', spent_pct: 96 },
];

const mockScoreDist: ScoreDist[] = [
  { range: '0-20', count: 2 },
  { range: '20-40', count: 8 },
  { range: '40-60', count: 18 },
  { range: '60-80', count: 24 },
  { range: '80-100', count: 12 },
];

const mockABTests: ABTestItem[] = [
  {
    id: '1',
    name: '落地页按钮文案测试',
    status: 'running',
    variant_count: 2,
    leading_variant: 'Variant_A',
    confidence: 0.94,
  },
  {
    id: '2',
    name: '头图素材对比',
    status: 'running',
    variant_count: 3,
    leading_variant: 'Control',
    confidence: 0.72,
  },
  {
    id: '3',
    name: '出价策略实验',
    status: 'stopped',
    variant_count: 2,
    leading_variant: 'Aggressive',
    confidence: 0.98,
  },
];

// ------------------------------------------------------------------
// 通用工具
// ------------------------------------------------------------------

function formatValue(value: number, unit: string): string {
  if (unit === '¥') return `¥${value.toFixed(2)}`;
  if (unit === '%') return `${value.toFixed(2)}%`;
  return `${value.toFixed(2)}${unit}`;
}

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

// ------------------------------------------------------------------
// Skeleton 组件
// ------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-4 w-20 bg-slate-700 rounded mb-3" />
      <div className="h-8 w-32 bg-slate-700 rounded mb-4" />
      <div className="h-16 w-full bg-slate-700/50 rounded" />
    </div>
  );
}

function SkeletonChart() {
  return (
    <div className="card p-5 animate-pulse">
      <div className="h-5 w-40 bg-slate-700 rounded mb-4" />
      <div className="h-[260px] w-full bg-slate-700/50 rounded" />
    </div>
  );
}

// ------------------------------------------------------------------
// KPI 卡片
// ------------------------------------------------------------------

interface KPICardProps {
  data: KPIData;
  loading?: boolean;
}

function KPICard({ data, loading }: KPICardProps) {
  const isPositive = data.change >= 0;

  if (loading) return <SkeletonCard />;

  return (
    <div className="card p-5 flex flex-col justify-between h-[164px]">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-muted text-sm">{data.label}</p>
          <p className="text-2xl font-semibold font-mono text-slate-100 mt-1">
            {formatValue(data.value, data.unit)}
          </p>
        </div>
        <div
          className={cn(
            'flex items-center gap-0.5 text-xs font-medium px-2 py-1 rounded-full',
            isPositive
              ? 'bg-success/10 text-success'
              : 'bg-danger/10 text-danger'
          )}
        >
          {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
          {Math.abs(data.change).toFixed(2)}%
        </div>
      </div>

      <div className="h-12 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.trend}>
            <defs>
              <linearGradient id={`gradient-${data.label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3B82F6"
              strokeWidth={2}
              fill={`url(#gradient-${data.label})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// RTB 趋势图
// ------------------------------------------------------------------

interface RTBTrendChartProps {
  data: WinRateTrendPoint[];
  loading?: boolean;
}

function RTBTrendChart({ data, loading }: RTBTrendChartProps) {
  if (loading) return <SkeletonChart />;

  const chartData = data.map((item) => ({
    time: item.label.slice(-5),
    avg_cpm: item.avg_cpm,
    win_rate: +(item.win_rate * 100).toFixed(2),
  }));

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-accent" />
        <h3 className="text-base font-semibold text-slate-100">RTB 竞价动态</h3>
      </div>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
            <YAxis
              yAxisId="left"
              stroke="#3B82F6"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `¥${v}`}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#10B981"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1E293B',
                border: '1px solid #334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#F1F5F9' }}
              itemStyle={{ color: '#CBD5E1' }}
            />
            <Legend wrapperStyle={{ paddingTop: '12px' }} />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="avg_cpm"
              name="平均 CPM"
              stroke="#3B82F6"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="win_rate"
              name="胜率"
              stroke="#10B981"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// DSP 预算状态
// ------------------------------------------------------------------

interface DSPBudgetStatusProps {
  data: DSPBudget[];
  loading?: boolean;
}

function DSPBudgetStatus({ data, loading }: DSPBudgetStatusProps) {
  if (loading) return <SkeletonChart />;

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-5">
        <TrendingUp size={18} className="text-warning" />
        <h3 className="text-base font-semibold text-slate-100">DSP 预算消耗</h3>
      </div>
      <div className="space-y-5">
        {data.map((dsp) => {
          const colorClass =
            dsp.spent_pct > 95
              ? 'bg-danger'
              : dsp.spent_pct > 80
              ? 'bg-warning'
              : 'bg-success';

          return (
            <div key={dsp.name}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-200 font-medium">{dsp.name}</span>
                <span
                  className={cn(
                    'font-mono font-medium',
                    dsp.spent_pct > 95
                      ? 'text-danger'
                      : dsp.spent_pct > 80
                      ? 'text-warning'
                      : 'text-success'
                  )}
                >
                  {dsp.spent_pct}%
                </span>
              </div>
              <div className="h-2.5 w-full bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-500', colorClass)}
                  style={{ width: `${dsp.spent_pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// 创意评分分布
// ------------------------------------------------------------------

interface CreativeScoreDistProps {
  data: ScoreDist[];
  loading?: boolean;
}

function CreativeScoreDist({ data, loading }: CreativeScoreDistProps) {
  if (loading) return <SkeletonChart />;

  return (
    <div className="card p-5">
      <h3 className="text-base font-semibold text-slate-100 mb-4">创意评分分布</h3>
      <div className="h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="range" stroke="#64748B" fontSize={12} tickLine={false} />
            <YAxis stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: '#334155', opacity: 0.4 }}
              contentStyle={{
                backgroundColor: '#1E293B',
                border: '1px solid #334155',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#F1F5F9' }}
              itemStyle={{ color: '#CBD5E1' }}
            />
            <Bar
              dataKey="count"
              name="创意数量"
              fill="#3B82F6"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// AB 测试概览
// ------------------------------------------------------------------

interface ABTestOverviewProps {
  data: ABTestItem[];
  loading?: boolean;
}

function ABTestOverview({ data, loading }: ABTestOverviewProps) {
  if (loading) return <SkeletonChart />;

  return (
    <div className="card p-5">
      <h3 className="text-base font-semibold text-slate-100 mb-4">A/B 测试状态</h3>
      <div className="space-y-3">
        {data.map((test) => (
          <div
            key={test.id}
            className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/30 hover:border-slate-600 transition-colors"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {test.status === 'running' && (
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success" />
                  </span>
                )}
                <span className="text-sm font-medium text-slate-100">{test.name}</span>
              </div>
              <div className="text-xs text-muted">
                {test.variant_count} 个变体 · 领先: {test.leading_variant}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-mono text-slate-100">
                {(test.confidence * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-muted">置信度</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Dashboard 主页面
// ------------------------------------------------------------------

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [trendData, setTrendData] = useState<WinRateTrendPoint[]>([]);

  // 生成 24 小时模拟趋势数据
  const mockTrendData: WinRateTrendPoint[] = useMemo(() => {
    const data: WinRateTrendPoint[] = [];
    for (let i = 0; i < 24; i++) {
      const hour = i.toString().padStart(2, '0') + ':00';
      data.push({
        label: hour,
        auctions: 120 + Math.floor(Math.random() * 80),
        wins: 60 + Math.floor(Math.random() * 50),
        win_rate: 0.3 + Math.random() * 0.4,
        avg_cpm: 6 + Math.random() * 6,
      });
    }
    return data;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchTrend() {
      try {
        const result = await apiRequest<WinRateTrendResponse>(
          '/dashboard/win-rate-trend?period=24h'
        );
        if (!cancelled && result.data.length > 0) {
          setTrendData(result.data);
        } else {
          setTrendData(mockTrendData);
        }
      } catch {
        setTrendData(mockTrendData);
      } finally {
        setLoading(false);
      }
    }

    fetchTrend();

    return () => {
      cancelled = true;
    };
  }, [mockTrendData]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">数据看板</h1>
        <p className="text-muted mt-1">广告投放全链路核心指标</p>
      </header>

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {mockKPIData.map((kpi) => (
          <KPICard key={kpi.label} data={kpi} loading={loading} />
        ))}
      </div>

      {/* RTB 趋势 + DSP 预算 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <RTBTrendChart data={trendData} loading={loading} />
        </div>
        <div>
          <DSPBudgetStatus data={mockDSPBudgets} loading={loading} />
        </div>
      </div>

      {/* 创意评分 + AB测试 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CreativeScoreDist data={mockScoreDist} loading={loading} />
        <ABTestOverview data={mockABTests} loading={loading} />
      </div>
    </div>
  );
}

export default Dashboard;
