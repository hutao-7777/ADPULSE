import { useMemo } from 'react';
import { Activity, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

import { cn } from '../../utils/cn';
import { flagLabel, GRADE_BG, GRADE_COLORS, GRADE_LABELS, SUB_LABELS } from './utils';
import type { FraudAlert, TrafficQuality } from './types';

interface TrafficPanelProps {
  quality: TrafficQuality;
  alerts: FraudAlert[];
  onResolve?: (id: string) => void;
}

export default function TrafficPanel({ quality, alerts, onResolve }: TrafficPanelProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="lg:col-span-1">
        <QualityScoreGauge quality={quality} />
      </div>
      <div className="lg:col-span-1">
        <SubDimensionBars quality={quality} />
      </div>
      <div className="lg:col-span-1">
        <FraudAlertList alerts={alerts} onResolve={onResolve} />
      </div>
    </div>
  );
}

function QualityScoreGauge({ quality }: { quality: TrafficQuality }) {
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
              stroke={
                quality.quality_score >= 90
                  ? '#10B981'
                  : quality.quality_score >= 70
                  ? '#3B82F6'
                  : quality.quality_score >= 50
                  ? '#F59E0B'
                  : '#EF4444'
              }
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
            <span
              className={cn(
                'text-xs font-medium px-2 py-0.5 rounded-full border mt-1',
                GRADE_BG[quality.grade],
                GRADE_COLORS[quality.grade]
              )}
            >
              {GRADE_LABELS[quality.grade]}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SubDimensionBars({ quality }: { quality: TrafficQuality }) {
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

function FraudAlertList({ alerts, onResolve }: { alerts: FraudAlert[]; onResolve?: (id: string) => void }) {
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
        {sorted.length === 0 && <p className="text-center text-muted text-sm py-6">暂无告警</p>}

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
