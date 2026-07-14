import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, DollarSign, Eye, MousePointerClick } from "lucide-react";
import apiClient from "../lib/apiClient";
import { cn } from "../utils/cn";

interface KPICard { label: string; value: number; unit: string; change: number; }
interface TrendPoint { date: string; impressions: number; revenue: number; }
interface PublisherSummary { impressions: number; clicks: number; conversions: number; revenue: number; ecpm: number; ctr: number; kpis: KPICard[]; }

const downloadCSV = async () => {
  try {
    const res = await apiClient.get("/api/report/summary?format=csv&days=7", { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a"); a.href = url; a.download = "adpulse_report_7d.csv"; a.click();
    URL.revokeObjectURL(url);
  } catch (e) { console.error("下载失败", e); }
};

const kpiConfig = [
  { key: "收入", icon: DollarSign, color: "text-green-400", bg: "bg-green-500/10" },
  { key: "eCPM", icon: Activity, color: "text-blue-400", bg: "bg-blue-500/10" },
  { key: "CTR", icon: MousePointerClick, color: "text-purple-400", bg: "bg-purple-500/10" },
  { key: "展示量", icon: Eye, color: "text-amber-400", bg: "bg-amber-500/10" },
];

function Dashboard() {
  const [summary, setSummary] = useState<PublisherSummary | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.all([apiClient.get("/api/dashboard/summary"), apiClient.get("/api/dashboard/trend")])
      .then(([s, t]) => { setSummary(s.data); setTrend(t.data.trend || []); })
      .catch(() => { setSummary({ impressions: 0, clicks: 0, conversions: 0, revenue: 0, ecpm: 0, ctr: 0, kpis: [{ label: "收入", value: 0, unit: "$", change: 0 }, { label: "eCPM", value: 0, unit: "$", change: 0 }, { label: "CTR", value: 0, unit: "%", change: 0 }, { label: "展示量", value: 0, unit: "", change: 0 }] }); })
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-8 h-8 border-2 border-accent border-t-transparent rounded-full" /></div>;
  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div><h1 className="text-2xl font-bold text-slate-100">发布商仪表盘</h1><p className="text-sm text-slate-400 mt-1">SDK 平台实时数据</p></div>
        <button onClick={downloadCSV} className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1">导出 CSV</button>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {summary?.kpis.map((kpi) => { const cfg = kpiConfig.find((c) => c.key === kpi.label); const Icon = cfg?.icon || Activity; return (
          <div key={kpi.label} className="card p-5">
            <div className="flex items-center justify-between mb-3"><span className="text-sm text-slate-400">{kpi.label}</span><div className={cn("p-2 rounded-lg", cfg?.bg)}><Icon size={18} className={cfg?.color} /></div></div>
            <div className="text-2xl font-bold text-slate-100">{kpi.label === "CTR" ? kpi.value.toFixed(2) + "%" : kpi.label === "eCPM" ? "$" + kpi.value.toFixed(2) : kpi.label === "收入" ? "$" + kpi.value.toFixed(2) : kpi.value.toLocaleString()}</div>
          </div>
        ); })}
      </div>
      <div className="card p-6">
        <h3 className="text-sm font-medium text-slate-300 mb-4">近 7 天趋势</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={trend}>
            <defs><linearGradient id="colorImps" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155"/><XAxis dataKey="date" stroke="#64748b" fontSize={12}/><YAxis stroke="#64748b" fontSize={12}/>
            <Tooltip contentStyle={{background:"#1e293b",border:"1px solid #334155",borderRadius:"8px"}}/>
            <Area type="monotone" dataKey="impressions" stroke="#3b82f6" fill="url(#colorImps)" strokeWidth={2}/>
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
export default Dashboard;

