import { useEffect, useRef, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Loader2,
  Play,
  RotateCcw,
  Zap,
  Server,
  Radio,
  Trophy,
} from 'lucide-react';

import { apiRequest } from '../utils/api';

// ------------------------------------------------------------------
// 类型定义
// ------------------------------------------------------------------

interface BidEntry {
  dsp: string;
  bid: number;
  response_time_ms: number;
}

interface WinnerInfo {
  dsp: string;
  winning_bid: number;
  settlement_price: number;
}

interface AuctionResult {
  impression_id: string;
  floor_price: number;
  auction_type: string;
  total_bids: number;
  bids: BidEntry[];
  winner: WinnerInfo | null;
  latency_ms: number;
}

interface BatchStats {
  total_auctions: number;
  filled_auctions: number;
  fill_rate: number;
  avg_winning_bid: number;
  avg_winning_cpm: number;
  total_latency_ms: number;
  avg_latency_ms: number;
  win_rate_by_dsp: Record<
    string,
    { wins: number; bids: number; win_rate: number }
  >;
}

interface BatchResponse {
  count: number;
  results: AuctionResult[];
  stats: BatchStats;
}

interface LogEntry {
  id: string;
  time: string;
  auctionNumber: number;
  bids: number;
  winner: string;
  price: string;
  latency: number;
}

interface FormState {
  auctionType: 'first_price' | 'second_price';
  floorPrice: number;
  userSegments: string[];
  deviceType: 'mobile' | 'desktop' | 'tablet';
  geo: 'tier1' | 'tier2' | 'tier3';
  adFormat: 'banner_300x250' | 'native' | 'video_15s';
}

// ------------------------------------------------------------------
// 常量与工具
// ------------------------------------------------------------------

const SEGMENT_OPTIONS = [
  'female',
  '25-34',
  'tech_enthusiast',
  'gamer',
  'premium',
];

const DSP_META: Record<string, { label: string; color: string; border: string; bg: string }> = {
  DSP_A: { label: 'DSP_A', color: '#3B82F6', border: 'border-blue-500', bg: 'bg-blue-500/10' },
  DSP_B: { label: 'DSP_B', color: '#A855F7', border: 'border-purple-500', bg: 'bg-purple-500/10' },
  DSP_C: { label: 'DSP_C', color: '#F97316', border: 'border-orange-500', bg: 'bg-orange-500/10' },
};

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}

function formatCpm(value: number): string {
  return `¥${(value * 1000).toFixed(2)}`;
}

function nowTime(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false });
}

// ------------------------------------------------------------------
// AuctionControls 控制面板
// ------------------------------------------------------------------

interface AuctionControlsProps {
  form: FormState;
  setForm: React.Dispatch<React.SetStateAction<FormState>>;
  onSingle: () => void;
  onBatch: () => void;
  loading: boolean;
}

function AuctionControls({ form, setForm, onSingle, onBatch, loading }: AuctionControlsProps) {
  const toggleSegment = (seg: string) => {
    setForm((prev) => ({
      ...prev,
      userSegments: prev.userSegments.includes(seg)
        ? prev.userSegments.filter((s) => s !== seg)
        : [...prev.userSegments, seg],
    }));
  };

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Radio size={18} className="text-accent" />
        <h2 className="text-base font-semibold text-slate-100">竞价参数控制</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* 拍卖类型 */}
        <div>
          <label className="block text-xs text-muted mb-2">拍卖类型</label>
          <div className="inline-flex rounded-lg bg-slate-800 p-1 border border-slate-700">
            {(['first_price', 'second_price'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setForm((p) => ({ ...p, auctionType: type }))}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-md transition-colors',
                  form.auctionType === type
                    ? 'bg-accent text-white'
                    : 'text-slate-300 hover:text-slate-100'
                )}
              >
                {type === 'first_price' ? 'First-Price' : 'Second-Price'}
              </button>
            ))}
          </div>
        </div>

        {/* 底价 */}
        <div>
          <label className="block text-xs text-muted mb-2">底价 (CPM)</label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={form.floorPrice}
            onChange={(e) => setForm((p) => ({ ...p, floorPrice: parseFloat(e.target.value) || 0 }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          />
        </div>

        {/* 设备 */}
        <div>
          <label className="block text-xs text-muted mb-2">设备类型</label>
          <select
            value={form.deviceType}
            onChange={(e) =>
              setForm((p) => ({ ...p, deviceType: e.target.value as FormState['deviceType'] }))
            }
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            <option value="mobile">Mobile</option>
            <option value="desktop">Desktop</option>
            <option value="tablet">Tablet</option>
          </select>
        </div>

        {/* 地域 */}
        <div>
          <label className="block text-xs text-muted mb-2">地域</label>
          <select
            value={form.geo}
            onChange={(e) => setForm((p) => ({ ...p, geo: e.target.value as FormState['geo'] }))}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            <option value="tier1">Tier 1</option>
            <option value="tier2">Tier 2</option>
            <option value="tier3">Tier 3</option>
          </select>
        </div>

        {/* 用户标签 */}
        <div className="md:col-span-2 lg:col-span-2">
          <label className="block text-xs text-muted mb-2">用户标签</label>
          <div className="flex flex-wrap gap-2">
            {SEGMENT_OPTIONS.map((seg) => (
              <button
                key={seg}
                onClick={() => toggleSegment(seg)}
                className={cn(
                  'px-3 py-1.5 text-xs rounded-full border transition-colors',
                  form.userSegments.includes(seg)
                    ? 'bg-accent/15 border-accent text-accent'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500'
                )}
              >
                {seg}
              </button>
            ))}
          </div>
        </div>

        {/* 广告格式 */}
        <div>
          <label className="block text-xs text-muted mb-2">广告格式</label>
          <select
            value={form.adFormat}
            onChange={(e) =>
              setForm((p) => ({ ...p, adFormat: e.target.value as FormState['adFormat'] }))
            }
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-accent"
          >
            <option value="banner_300x250">Banner 300x250</option>
            <option value="native">Native</option>
            <option value="video_15s">Video 15s</option>
          </select>
        </div>

        {/* 操作按钮 */}
        <div className="flex items-end gap-3">
          <button
            onClick={onSingle}
            disabled={loading}
            className="btn-primary flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            运行单次竞价
          </button>
          <button
            onClick={onBatch}
            disabled={loading}
            className="btn-secondary flex items-center gap-2 disabled:opacity-60"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            批量模拟 (100次)
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// AuctionFlowViz 单次竞价流程可视化
// ------------------------------------------------------------------

interface AuctionFlowVizProps {
  result: AuctionResult | null;
  step: number;
}

function FlowNode({
  icon: Icon,
  label,
  sub,
  active,
}: {
  icon: React.ElementType;
  label: string;
  sub?: string;
  active?: boolean;
}) {
  return (
    <div
      className={cn(
        'relative flex flex-col items-center justify-center w-28 h-28 rounded-2xl border-2 transition-all duration-500 z-10',
        active
          ? 'bg-accent/15 border-accent shadow-[0_0_24px_rgba(59,130,246,0.35)]'
          : 'bg-secondary border-slate-700'
      )}
    >
      <Icon size={28} className={active ? 'text-accent' : 'text-muted'} />
      <span className="text-sm font-medium text-slate-100 mt-2">{label}</span>
      {sub && <span className="text-xs text-muted mt-0.5">{sub}</span>}
    </div>
  );
}

function Arrow({ visible, label, color = '#3B82F6', reverse = false }: {
  visible: boolean;
  label?: string;
  color?: string;
  reverse?: boolean;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center transition-all duration-500',
        visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-2'
      )}
      style={{ transform: reverse && !visible ? 'translateX(-8px)' : undefined }}
    >
      <div className="relative flex items-center w-20 h-0.5" style={{ backgroundColor: color }}>
        <div
          className="absolute right-0 w-0 h-0 border-y-4 border-y-transparent"
          style={{
            borderLeftWidth: '6px',
            borderLeftStyle: 'solid',
            borderLeftColor: color,
            transform: reverse ? 'rotate(180deg) translateX(6px)' : 'none',
            left: reverse ? '-6px' : 'auto',
            right: reverse ? 'auto' : '-6px',
          }}
        />
      </div>
      {label && (
        <span className="text-[10px] mt-1.5 px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 whitespace-nowrap">
          {label}
        </span>
      )}
    </div>
  );
}

function BidCard({ bid, isWinner, visible }: { bid: BidEntry; isWinner: boolean; visible: boolean }) {
  const meta = DSP_META[bid.dsp] || {
    label: bid.dsp,
    color: '#94A3B8',
    border: 'border-slate-500',
    bg: 'bg-slate-500/10',
  };

  return (
    <div
      className={cn(
        'relative w-full p-3 rounded-xl border-2 transition-all duration-500',
        meta.border,
        meta.bg,
        visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4',
        isWinner && 'ring-2 ring-yellow-400/60 shadow-[0_0_20px_rgba(250,204,21,0.35)]'
      )}
    >
      {isWinner && (
        <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-yellow-400 text-slate-900">
          <Trophy size={12} strokeWidth={3} />
        </span>
      )}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold" style={{ color: meta.color }}>
          {meta.label}
        </span>
        <span className="text-xs text-muted">{bid.response_time_ms}ms</span>
      </div>
      <div className="text-lg font-mono font-semibold text-slate-100 mt-1">
        {formatCpm(bid.bid)}
      </div>
      <div className="text-[10px] text-muted">CPM</div>
    </div>
  );
}

function AuctionFlowViz({ result, step }: AuctionFlowVizProps) {
  if (!result) {
    return (
      <div className="card p-8 min-h-[420px] flex flex-col items-center justify-center text-center">
        <Server size={48} className="text-muted mb-4" />
        <p className="text-muted">点击“运行单次竞价”查看完整竞价流程可视化</p>
      </div>
    );
  }

  const sortedBids = [...result.bids].sort((a, b) => b.bid - a.bid);
  const winner = result.winner;

  return (
    <div className="card p-6 overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-base font-semibold text-slate-100">单次竞价流程</h3>
        <div className="text-xs text-muted">
          Auction ID: <span className="font-mono text-slate-300">{result.impression_id.slice(0, 8)}</span>
          {' · '}
          类型: <span className="text-slate-300">{result.auction_type === 'first_price' ? 'First-Price' : 'Second-Price'}</span>
        </div>
      </div>

      <div className="relative flex items-center justify-between min-h-[340px] px-4">
        {/* SSP */}
        <div className="flex flex-col items-center gap-4">
          <FlowNode icon={Server} label="SSP" sub="发布商" active={step >= 1 && step <= 5} />
        </div>

        {/* Arrow 1: SSP -> ADX */}
        <div className="flex-1 flex justify-center px-2">
          <Arrow visible={step >= 1} label="Bid Request" />
        </div>

        {/* ADX */}
        <div className="flex flex-col items-center gap-4 z-20">
          <FlowNode icon={Radio} label="ADX" sub="广告交易平台" active={step >= 2 && step <= 4} />
          {step >= 4 && winner && (
            <div className="mt-2 p-3 rounded-xl bg-yellow-400/10 border border-yellow-400/50 text-center animate-pulse">
              <div className="text-xs text-yellow-200 mb-1">结算价格</div>
              <div className="text-xl font-mono font-bold text-yellow-400">
                {formatCpm(winner.settlement_price)}
              </div>
              {result.auction_type === 'second_price' && winner.settlement_price < winner.winning_bid && (
                <div className="text-[10px] text-yellow-200/80 mt-1">
                  Winner 出价 {formatCpm(winner.winning_bid)}，实际支付 {formatCpm(winner.settlement_price)}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Arrow 2: ADX -> DSPs */}
        <div className="flex-1 flex justify-center px-2 relative">
          <div
            className={cn(
              'flex flex-col gap-8 transition-all duration-500',
              step >= 2 ? 'opacity-100' : 'opacity-0'
            )}
          >
            <Arrow visible={step >= 2} label="请求出价" />
            <Arrow visible={step >= 2} label="请求出价" />
            <Arrow visible={step >= 2} label="请求出价" />
          </div>
        </div>

        {/* DSPs */}
        <div className="flex flex-col gap-3 w-40">
          {sortedBids.map((bid) => (
            <BidCard
              key={bid.dsp}
              bid={bid}
              isWinner={winner?.dsp === bid.dsp}
              visible={step >= 3}
            />
          ))}
        </div>

        {/* Arrow 3: DSPs -> ADX (返回出价) */}
        <div
          className={cn(
            'absolute right-[168px] top-1/2 -translate-y-1/2 flex flex-col gap-[88px] transition-all duration-500',
            step >= 3 ? 'opacity-100' : 'opacity-0'
          )}
        >
          {sortedBids.map((bid) => (
            <div key={bid.dsp} className="flex items-center">
              <Arrow visible={step >= 3} label={`${formatCpm(bid.bid)}`} reverse />
            </div>
          ))}
        </div>

        {/* Arrow 4: ADX -> SSP (返回广告) */}
        <div className="absolute left-1/2 -translate-x-1/2 bottom-8 flex flex-col items-center transition-all duration-500">
          <Arrow visible={step >= 5} label="Win Notice + 广告" reverse />
        </div>
      </div>

      {/* 步骤指示器 */}
      <div className="flex items-center justify-center gap-2 mt-6">
        {['SSP 发起请求', 'ADX 广播', 'DSP 出价', '决出赢家', '返回广告'].map((label, idx) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={cn(
                'w-2.5 h-2.5 rounded-full transition-colors',
                step > idx ? 'bg-accent' : 'bg-slate-700'
              )}
            />
            <span
              className={cn(
                'text-[10px] transition-colors',
                step > idx ? 'text-slate-200' : 'text-muted'
              )}
            >
              {label}
            </span>
            {idx < 4 && <div className="w-4 h-px bg-slate-700 mx-1" />}
          </div>
        ))}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// BatchResults 批量结果统计
// ------------------------------------------------------------------

interface BatchResultsProps {
  result: BatchResponse | null;
}

function BatchResults({ result }: BatchResultsProps) {
  if (!result) return null;

  const { stats } = result;
  const dspKeys = Object.keys(stats.win_rate_by_dsp);

  const dspRows = dspKeys.map((name) => {
    const d = stats.win_rate_by_dsp[name];
    return {
      name,
      bids: d.bids,
      wins: d.wins,
      winRate: +(d.win_rate * 100).toFixed(1),
    };
  });

  const chartData = dspRows.map((r) => ({ name: r.name, 出价次数: r.bids, 胜场: r.wins }));

  return (
    <div className="space-y-4">
      {/* 汇总卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: '总拍卖次数', value: stats.total_auctions },
          { label: '成交次数', value: stats.filled_auctions },
          { label: '填充率', value: `${(stats.fill_rate * 100).toFixed(1)}%` },
          { label: '平均结算CPM', value: formatCpm(stats.avg_winning_bid) },
          { label: '平均延迟', value: `${stats.avg_latency_ms.toFixed(0)}ms` },
        ].map((item) => (
          <div key={item.label} className="card p-4 text-center">
            <p className="text-muted text-xs">{item.label}</p>
            <p className="text-xl font-mono font-semibold text-slate-100 mt-1">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* DSP 表现表 */}
        <div className="card p-5">
          <h4 className="text-sm font-semibold text-slate-100 mb-3">DSP 表现对比</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-slate-700">
                  <th className="pb-2 font-medium">DSP</th>
                  <th className="pb-2 font-medium">出价次数</th>
                  <th className="pb-2 font-medium">胜场</th>
                  <th className="pb-2 font-medium">胜率</th>
                </tr>
              </thead>
              <tbody>
                {dspRows.map((row) => (
                  <tr key={row.name} className="border-b border-slate-800 last:border-0">
                    <td className="py-3 font-medium text-slate-200">{row.name}</td>
                    <td className="py-3 font-mono text-slate-300">{row.bids}</td>
                    <td className="py-3 font-mono text-slate-300">{row.wins}</td>
                    <td className="py-3">
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-medium',
                          row.winRate >= 50
                            ? 'bg-success/10 text-success'
                            : row.winRate >= 30
                            ? 'bg-warning/10 text-warning'
                            : 'bg-muted/10 text-muted'
                        )}
                      >
                        {row.winRate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 出价分布 */}
        <div className="card p-5">
          <h4 className="text-sm font-semibold text-slate-100 mb-3">DSP 出价与胜场分布</h4>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 5, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="name" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1E293B',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: '#F1F5F9' }}
                  itemStyle={{ color: '#CBD5E1' }}
                />
                <Bar dataKey="出价次数" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="胜场" fill="#10B981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// AuctionLog 实时日志
// ------------------------------------------------------------------

interface AuctionLogProps {
  logs: LogEntry[];
}

function AuctionLog({ logs }: AuctionLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700/50 bg-slate-800/30">
        <h3 className="text-sm font-semibold text-slate-100">竞价日志</h3>
        <span className="text-xs text-muted">保留最近 50 条</span>
      </div>
      <div className="h-48 overflow-y-auto p-3 space-y-1.5 font-mono text-xs">
        {logs.length === 0 && (
          <div className="text-muted text-center py-10">暂无日志</div>
        )}
        {logs.map((log) => (
          <div
            key={log.id}
            className="flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-800/40 border border-slate-700/30"
          >
            <span className="text-muted">[{log.time}]</span>
            <span className="text-slate-300">Auction #{log.auctionNumber}</span>
            <span className="text-muted">{log.bids} bids</span>
            <span
              className={cn(
                'font-medium',
                log.winner === 'None' ? 'text-muted' : 'text-success'
              )}
            >
              {log.winner === 'None' ? '无赢家' : `${log.winner} wins`}
            </span>
            <span className="text-slate-200">{log.price}</span>
            <span className="text-muted ml-auto">{log.latency}ms</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// RTBEngine 主页面
// ------------------------------------------------------------------

function RTBEngine() {
  const [form, setForm] = useState<FormState>({
    auctionType: 'second_price',
    floorPrice: 3.0,
    userSegments: ['female', '25-34'],
    deviceType: 'mobile',
    geo: 'tier1',
    adFormat: 'banner_300x250',
  });

  const [loading, setLoading] = useState(false);
  const [auctionResult, setAuctionResult] = useState<AuctionResult | null>(null);
  const [flowStep, setFlowStep] = useState(0);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [auctionCounter, setAuctionCounter] = useState(0);

  // 动画推进
  useEffect(() => {
    if (!auctionResult) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    setFlowStep(1);
    timers.push(setTimeout(() => setFlowStep(2), 500));
    timers.push(setTimeout(() => setFlowStep(3), 1000));
    timers.push(setTimeout(() => setFlowStep(4), 1600));
    timers.push(setTimeout(() => setFlowStep(5), 2200));

    return () => timers.forEach(clearTimeout);
  }, [auctionResult]);

  const addLog = (result: AuctionResult) => {
    const nextCount = auctionCounter + 1;
    setAuctionCounter(nextCount);
    const entry: LogEntry = {
      id: `${Date.now()}-${nextCount}`,
      time: nowTime(),
      auctionNumber: nextCount,
      bids: result.total_bids,
      winner: result.winner?.dsp || 'None',
      price: result.winner ? formatCpm(result.winner.settlement_price) : '¥0.00',
      latency: result.latency_ms,
    };
    setLogs((prev) => [...prev.slice(-49), entry]);
  };

  const runSingleAuction = async () => {
    setLoading(true);
    setAuctionResult(null);
    setFlowStep(0);
    setBatchResult(null);

    try {
      const payload = {
        floor_price: form.floorPrice / 1000,
        user_segments: form.userSegments,
        device_type: form.deviceType,
        geo: form.geo,
        ad_format: form.adFormat,
        context_category: 'ecommerce',
        auction_type: form.auctionType,
      };

      const result = await apiRequest<AuctionResult>('/rtb/auction/single', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setAuctionResult(result);
      addLog(result);
    } catch (err) {
      console.error('单次竞价失败:', err);
      alert(err instanceof Error ? err.message : '请求失败');
    } finally {
      setLoading(false);
    }
  };

  const runBatchAuction = async () => {
    setLoading(true);
    setAuctionResult(null);
    setFlowStep(0);

    try {
      const result = await apiRequest<BatchResponse>('/rtb/auction/batch', {
        method: 'POST',
        body: JSON.stringify({
          count: 100,
          auction_type: form.auctionType,
          campaign_config: {},
        }),
      });

      setBatchResult(result);
      result.results.forEach((r) => addLog(r));
    } catch (err) {
      console.error('批量模拟失败:', err);
      alert(err instanceof Error ? err.message : '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-100">RTB 竞价引擎</h1>
        <p className="text-muted mt-1">程序化广告实时竞价流程可视化与模拟</p>
      </header>

      <AuctionControls
        form={form}
        setForm={setForm}
        onSingle={runSingleAuction}
        onBatch={runBatchAuction}
        loading={loading}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <AuctionFlowViz result={auctionResult} step={flowStep} />
        </div>
        <div>
          <BatchResults result={batchResult} />
          {!batchResult && (
            <div className="card p-6 h-full min-h-[200px] flex flex-col items-center justify-center text-center">
              <RotateCcw size={40} className="text-muted mb-3" />
              <p className="text-muted text-sm">点击“批量模拟 (100次)”查看统计结果</p>
            </div>
          )}
        </div>
      </div>

      <AuctionLog logs={logs} />
    </div>
  );
}

export default RTBEngine;
