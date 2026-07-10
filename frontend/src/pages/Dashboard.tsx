import { useEffect, useState } from 'react';
import {
  Area,
  AreaChart,
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
import DataSourceBadge from '../components/DataSourceBadge';
import { cn } from '../utils/cn';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface KPIData {
  label: string;
  value: number;
  unit: string;
  change: number;
  trend: number[];
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

interface ABTestItem {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'draft';
  variant_count: number;
  leading_variant: string;
  confidence: number;
}

// ------------------------------------------------------------------
// Fallback 数据
// ------------------------------------------------------------------

const fallbackKPIData: KPIData[] = [
  { label: 'eCPM', value: 0, unit: '¥', change: 0, trend: [0, 0, 0, 0, 0, 0, 0] },
  { label: 'CTR', value: 0, unit: '%', change: 0, trend: [0, 0, 0, 0, 0, 0, 0] },
  { label: 'Fill Rate', value: 0, unit: '%', change: 0, trend: [0, 0, 0, 0, 0, 0, 0] },
  { label: 'ROI', value: 0, unit: 'x', change: 0, trend: [0, 0, 0, 0, 0, 0, 0] },
];

const fallbackDSPBudgets: DSPBudget[] = [];
const fallbackABTests: ABTestItem[] = [];

// ------------------------------------------------------------------
// 通用工具
// ------------------------------------------------------------------

function formatValue(value: number, unit: string): string {
  if (unit === '¥') return `¥${value.toFixed(2)}`;
  if (unit === '%') return `${value.toFixed(2)}%`;
  return `${value.toFixed(2)}${unit}`;
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
    <div className="card p-5 flex flex-col justify-between min-h-[164px]">
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
            isPositive ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
          )}
        >
          {isPositive ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
          {Math.abs(data.change).toFixed(2)}%
        </div>
      </div>

      <div className="h-12 -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.trend.map((v, i) => ({ label: `T-${6 - i}`, value: v }))}>
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

  if (data.length === 0) {
    return (
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-accent" />
          <h3 className="text-base font-semibold text-slate-100">RTB 竞价动态</h3>
        </div>
        <div className="h-[300px] flex items-center justify-center text-muted text-sm">
          暂无 RTB 数据
        </div>
      </div>
    );
  }

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
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
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
// Campaign 预算状态
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
        <h3 className="text-base font-semibold text-slate-100">Campaign 预算消耗</h3>
      </div>
      <div className="space-y-5">
        {data.length === 0 && (
          <p className="text-center text-muted text-sm py-6">暂无预算数据</p>
        )}
        {data.map((dsp) => {
          const colorClass =
            dsp.spent_pct > 95 ? 'bg-danger' : dsp.spent_pct > 80 ? 'bg-warning' : 'bg-success';

          return (
            <div key={dsp.name}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-200 font-medium">{dsp.name}</span>
                <span
                  className={cn(
                    'font-mono font-medium',
                    dsp.spent_pct > 95 ? 'text-danger' : dsp.spent_pct > 80 ? 'text-warning' : 'text-success'
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
        {data.length === 0 && (
          <p className="text-center text-muted text-sm py-6">暂无运行中实验</p>
        )}
        {data.map((test) => (
          <div
            key={test.id}
            className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700/30 hover:border-slate-600 transition-colors"
          >
            <div className="space-y-1 min-w-0 flex-1 pr-4">
              <div className="flex items-center gap-2">
                {test.status === 'running' && (
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-success" />
                  </span>
                )}
                <span className="text-sm font-medium text-slate-100 truncate">{test.name}</span>
              </div>
              <div className="text-xs text-muted">
                {test.variant_count} 个变体 · 领先: {test.leading_variant}
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <div className="text-sm font-mono text-slate-100">{test.confidence.toFixed(0)}%</div>
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
  const [kpiData, setKpiData] = useState<KPIData[]>(fallbackKPIData);
  const [dspBudgets, setDspBudgets] = useState<DSPBudget[]>(fallbackDSPBudgets);
  const [abTests, setAbTests] = useState<ABTestItem[]>(fallbackABTests);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      try {
        const [trend, kpi, budgets, overview] = await Promise.all([
          apiRequest<WinRateTrendResponse>('/dashboard/win-rate-trend?period=7d'),
          apiRequest<{ kpis: KPIData[] }>('/dashboard/kpi-summary'),
          apiRequest<{ budgets: DSPBudget[] }>('/dashboard/campaign-budgets'),
          apiRequest<{ experiments: ABTestItem[] }>('/dashboard/abtest-overview'),
        ]);
        if (!cancelled) {
          setTrendData(trend.data || []);
          setKpiData(kpi.kpis?.length > 0 ? kpi.kpis : fallbackKPIData);
          setDspBudgets(budgets.budgets?.length > 0 ? budgets.budgets : fallbackDSPBudgets);
          setAbTests(overview.experiments?.length > 0 ? overview.experiments : fallbackABTests);
        }
      } catch (err) {
        console.error('Dashboard 数据加载失败:', err);
        if (!cancelled) {
          setTrendData([]);
          setKpiData(fallbackKPIData);
          setDspBudgets(fallbackDSPBudgets);
          setAbTests(fallbackABTests);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-100">数据看板</h1>
          <DataSourceBadge />
        </div>
        <p className="text-muted mt-1">广告投放全链路核心指标</p>
      </header>

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiData.map((kpi) => (
          <KPICard key={kpi.label} data={kpi} loading={loading} />
        ))}
      </div>

      {/* RTB 趋势 + Campaign 预算 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <RTBTrendChart data={trendData} loading={loading} />
        </div>
        <div>
          <DSPBudgetStatus data={dspBudgets} loading={loading} />
        </div>
      </div>

      {/* A/B 测试状态 */}
      <div className="grid grid-cols-1 gap-4">
        <ABTestOverview data={abTests} loading={loading} />
      </div>
    </div>
  );
}

export default Dashboard;
