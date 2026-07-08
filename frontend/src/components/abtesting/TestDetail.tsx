import { Activity, AlertTriangle, Play, Square, Trash2 } from 'lucide-react';

import { cn } from '../../utils/cn';
import ResultChart from './ResultChart';
import { formatDate, formatMetric, getStatusBadge, metricLabel } from './utils';
import type { ABTest, AnomalyAlert, TestResults, VariantStat } from './types';

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

export default function TestDetail({
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
        <Activity className="w-8 h-8 text-accent animate-spin" />
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
          <div className="card p-5">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Variant 对比</h3>
            <VariantComparisonTable variants={results.variants} />
          </div>

          <ResultChart variants={results.variants} metric={test.metric_target} />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {results.variants
              .filter((v) => v.name.toLowerCase() !== 'control')
              .map((variant) => (
                <VariantSummaryCard
                  key={variant.name}
                  variant={variant}
                  metric={test.metric_target}
                  controlMetricValue={controlMetricValue}
                />
              ))}

            <div className="card p-5 lg:col-span-2">
              <h4 className="text-sm font-semibold text-slate-100 mb-2">推荐结论</h4>
              <p className="text-sm text-slate-300 leading-relaxed">{results.recommendation}</p>
            </div>
          </div>
        </>
      )}

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

function VariantComparisonTable({ variants }: { variants: VariantStat[] }) {
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
                <td className="py-3 px-2 font-mono text-slate-300">
                  {(variant.conversion_rate * 100).toFixed(2)}%
                </td>
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

function VariantSummaryCard({
  variant,
  metric,
  controlMetricValue,
}: {
  variant: VariantStat;
  metric: string;
  controlMetricValue: number;
}) {
  const metricValue =
    metric === 'ctr'
      ? variant.ctr
      : metric === 'conversion_rate'
      ? variant.conversion_rate
      : variant.roi;
  const lower = controlMetricValue + variant.confidence_interval[0];
  const upper = controlMetricValue + variant.confidence_interval[1];
  const margin = (upper - lower) / 2;

  return (
    <div className="card p-5">
      <h4 className="text-sm font-semibold text-slate-100 mb-3">{variant.name} 统计摘要</h4>
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-muted">95% 置信区间</span>
          <span className="font-mono text-slate-200">
            {formatMetric(metricValue, metric)} ± {formatMetric(margin, metric)}
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
          {variant.power >= 0.8 ? '样本量充足' : '建议增加样本量以提升统计可信度'}
        </div>
      </div>
    </div>
  );
}
