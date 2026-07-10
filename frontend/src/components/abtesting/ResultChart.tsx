import { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { TrendingUp } from 'lucide-react';

import type { DailyStat, TrendData } from './types';

interface ResultChartProps {
  trendData: TrendData | null;
  metric: string;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A855F7'];

function getMetricValue(day: DailyStat, metric: string): number {
  if (metric === 'ctr') return day.ctr ?? 0;
  if (metric === 'conversion_rate') return day.conversion_rate ?? 0;
  if (metric === 'revenue') return day.revenue ?? 0;
  return day.ctr ?? 0;
}

function formatYAxis(v: number, metric: string): string {
  if (metric === 'revenue') return `¥${v.toFixed(0)}`;
  return `${(v * 100).toFixed(1)}%`;
}

function formatTooltip(v: number, metric: string): string {
  if (metric === 'revenue') return `¥${v.toFixed(2)}`;
  return `${(v * 100).toFixed(2)}%`;
}

export default function ResultChart({ trendData, metric }: ResultChartProps) {
  const data = useMemo(() => {
    if (!trendData || !trendData.variants || trendData.variants.length === 0) {
      return [];
    }

    const dates = trendData.variants[0].daily.map((d) => d.date_label);
    return dates.map((label, i) => {
      const point: Record<string, number | string> = { date: label };
      trendData.variants.forEach((v) => {
        const day = v.daily[i];
        if (day) {
          point[v.name] = getMetricValue(day, metric);
        }
      });
      return point;
    });
  }, [trendData, metric]);

  const variantNames = useMemo(() => {
    if (!trendData) return [];
    return trendData.variants.map((v) => v.name);
  }, [trendData]);

  if (!trendData || data.length === 0) {
    return (
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={18} className="text-accent" />
          <h3 className="text-base font-semibold text-slate-100">趋势对比</h3>
        </div>
        <div className="h-[280px] flex items-center justify-center text-slate-500 text-sm">
          暂无趋势数据 — 运行实验后将自动产生
        </div>
      </div>
    );
  }

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
              tickFormatter={(v) => formatYAxis(v, metric)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#f1f5f9',
                fontSize: '12px',
              }}
              formatter={(value: any, name: string) => [
                formatTooltip(Number(value), metric),
                name,
              ]}
            />
            <Legend wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
            {variantNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
