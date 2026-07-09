import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import apiClient from '../lib/apiClient';

interface DailyStat {
  id: string;
  date: string;
  advertiser_id: string | null;
  impressions: number;
  clicks: number;
  conversions: number;
  total_cost: number;
  avg_ctr: number;
}

interface Summary {
  total_bids: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_cost: number;
  avg_ctr: number;
  avg_cpm: number;
}

interface Auction {
  id: string;
  bid_id: string;
  timestamp: string;
  advertiser_id: string | null;
  region: number | null;
  city: number | null;
  ad_exchange: number | null;
  creative_id: string | null;
  bidding_price: number;
  paying_price: number;
  is_win: boolean;
  is_clicked: boolean;
  is_converted: boolean;
}

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
}

function MetricCard({ label, value, sub }: MetricCardProps) {
  return (
    <div className="bg-secondary rounded-xl p-5 border border-slate-700/50">
      <p className="text-muted text-sm mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(2)}K`;
  return num.toLocaleString();
}

function formatMoney(num: number): string {
  return `¥${num.toFixed(2)}`;
}

function IpinyouData() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [daily, setDaily] = useState<DailyStat[]>([]);
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [summaryRes, dailyRes, auctionsRes] = await Promise.all([
          apiClient.get('/v1/ipinyou/stats/summary'),
          apiClient.get('/v1/ipinyou/stats/daily'),
          apiClient.get('/v1/ipinyou/auctions?page=1&page_size=20'),
        ]);
        setSummary(summaryRes.data.data);
        setDaily(dailyRes.data.data);
        setAuctions(auctionsRes.data.data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载 iPinYou 数据失败');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const chartData = useMemo(
    () =>
      daily.map((d) => ({
        date: d.date.slice(0, 10),
        impressions: d.impressions,
        clicks: d.clicks,
        cost: Number(d.total_cost.toFixed(2)),
      })),
    [daily]
  );

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        加载 iPinYou 数据中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-danger">
        {error}
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">iPinYou RTB 数据集</h1>
        <p className="text-muted text-sm mt-1">
          接入真实竞价、曝光、点击与转化数据，按天聚合展示核心指标。
        </p>
      </div>

      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="总曝光"
            value={formatNumber(summary.total_impressions)}
            sub={`${formatNumber(summary.total_bids)} 次竞价`}
          />
          <MetricCard
            label="总点击"
            value={formatNumber(summary.total_clicks)}
            sub={`CTR ${(summary.avg_ctr * 100).toFixed(3)}%`}
          />
          <MetricCard
            label="总转化"
            value={formatNumber(summary.total_conversions)}
          />
          <MetricCard
            label="总消耗"
            value={formatMoney(summary.total_cost)}
            sub={`平均 CPM ${formatMoney(summary.avg_cpm)}`}
          />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-secondary rounded-xl p-5 border border-slate-700/50">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">
            日曝光 / 点击趋势
          </h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '0.5rem',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="impressions"
                  name="曝光"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="clicks"
                  name="点击"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-secondary rounded-xl p-5 border border-slate-700/50">
          <h2 className="text-lg font-semibold text-slate-100 mb-4">日消耗</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '0.5rem',
                  }}
                />
                <Bar dataKey="cost" name="消耗 (CNY)" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-secondary rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="p-5 border-b border-slate-700/50">
          <h2 className="text-lg font-semibold text-slate-100">最近竞价记录</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800/50 text-slate-300">
              <tr>
                <th className="px-4 py-3 font-medium">BidID</th>
                <th className="px-4 py-3 font-medium">时间</th>
                <th className="px-4 py-3 font-medium">广告主</th>
                <th className="px-4 py-3 font-medium">出价</th>
                <th className="px-4 py-3 font-medium">胜出</th>
                <th className="px-4 py-3 font-medium">点击</th>
                <th className="px-4 py-3 font-medium">转化</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {auctions.map((auction) => (
                <tr key={auction.id} className="hover:bg-slate-700/20">
                  <td className="px-4 py-3 font-mono text-slate-300 truncate max-w-[180px]">
                    {auction.bid_id}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {new Date(auction.timestamp).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{auction.advertiser_id || '-'}</td>
                  <td className="px-4 py-3 text-slate-300">{formatMoney(auction.bidding_price)}</td>
                  <td className="px-4 py-3">
                    {auction.is_win ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-success/10 text-success">
                        是
                      </span>
                    ) : (
                      <span className="text-slate-500">否</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {auction.is_clicked ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-accent/10 text-accent">
                        是
                      </span>
                    ) : (
                      <span className="text-slate-500">否</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {auction.is_converted ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning/10 text-warning">
                        是
                      </span>
                    ) : (
                      <span className="text-slate-500">否</span>
                    )}
                  </td>
                </tr>
              ))}
              {auctions.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-muted">
                    暂无竞价数据，请先运行导入脚本。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default IpinyouData;
