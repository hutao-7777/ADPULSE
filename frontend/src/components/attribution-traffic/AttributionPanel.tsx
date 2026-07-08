import { useMemo } from 'react';
import { ArrowRight, BarChart3, TrendingUp } from 'lucide-react';

import { cn } from '../../utils/cn';
import { mockAttribution } from '../../utils/mockData';
import { channelColor, channelLabel, formatTime, MODELS, MODEL_LABELS } from './utils';
import type { AttributionResult } from './types';

interface AttributionPanelProps {
  attribution: AttributionResult | null;
  activeModel: string;
  onModelChange: (model: string) => void;
}

export default function AttributionPanel({ attribution, activeModel, onModelChange }: AttributionPanelProps) {
  const data = attribution || (mockAttribution as AttributionResult);
  const activeCredits = data.model_credits?.[activeModel] || {};

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
      <div className="lg:col-span-3 space-y-4">
        <AttributionModelTabs activeModel={activeModel} onChange={onModelChange} />
        <UserJourneyTimeline
          journey={data.journey || []}
          credits={activeCredits}
          conversionValue={data.conversion_value || 0}
        />
        {data.summary && <div className="card p-4 text-sm text-slate-300">{data.summary}</div>}
      </div>
      <div className="lg:col-span-2">
        <ModelComparisonTable modelCredits={data.model_credits || mockAttribution.model_credits} />
      </div>
    </div>
  );
}

function AttributionModelTabs({ activeModel, onChange }: { activeModel: string; onChange: (model: string) => void }) {
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

function UserJourneyTimeline({
  journey,
  credits,
  conversionValue,
}: {
  journey: AttributionResult['journey'];
  credits: Record<string, number>;
  conversionValue: number;
}) {
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

                  <div className="absolute bottom-full mb-2 hidden group-hover:block z-10 w-40 bg-slate-900 border border-slate-700 rounded-lg p-2 shadow-xl">
                    <p className="text-xs text-slate-100 font-medium">{channelLabel(step.channel)}</p>
                    <p className="text-[10px] text-muted">{step.event_type}</p>
                    <p className="text-[10px] text-muted">{formatTime(step.event_time)}</p>
                    <p className="text-[10px] text-accent mt-1">功劳: ¥{(credit * conversionValue).toFixed(2)}</p>
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

function ModelComparisonTable({ modelCredits }: { modelCredits: Record<string, Record<string, number>> }) {
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
                <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ backgroundColor: channelColor(channel) }} />
                {channelLabel(channel)}
              </td>
              {MODELS.map((model) => {
                const value = modelCredits[model]?.[channel] || 0;
                return (
                  <td key={model} className="py-2 text-right">
                    <span
                      className="px-2 py-0.5 rounded font-mono"
                      style={{ backgroundColor: `rgba(59, 130, 246, ${value * 0.6})` }}
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
