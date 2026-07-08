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

import type { VariantStat } from './types';

interface ResultChartProps {
  variants: VariantStat[];
  metric: string;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A855F7'];

export default function ResultChart({ variants, metric }: ResultChartProps) {
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
