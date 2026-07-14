import { useEffect, useState } from "react";
import { AlertTriangle, Shield, ShieldAlert, ShieldCheck, TrendingUp, Activity, Loader2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import apiClient from "../lib/apiClient";
import { cn } from "../utils/cn";

interface AdUnit { id: string; name: string; ad_format: string; }
interface QualityResult { ad_unit_id: string; quality_score: number; grade: string; ctr_score: number; cvr_score: number; bounce_score: number; dwell_score: number; interaction_score: number; flags: string[]; impressions: number; clicks: number; conversions: number; }
interface AlertItem { id: string; alert_type: string; severity: string; description: string; detected_at: string; status: string; }
interface TrendPoint { date: string; quality_score: number; grade: string; }

const gradeConfig: Record<string, { icon: any; color: string; bg: string; label: string }> = {
  premium: { icon: ShieldCheck, color: "text-green-400", bg: "bg-green-500/10", label: "优质" },
  standard: { icon: Shield, color: "text-blue-400", bg: "bg-blue-500/10", label: "标准" },
  low: { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10", label: "低质" },
  fraud: { icon: ShieldAlert, color: "text-red-400", bg: "bg-red-500/10", label: "疑似作弊" },
};

function TrafficQuality() {
  const [adUnits, setAdUnits] = useState<AdUnit[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<string>("");
  const [quality, setQuality] = useState<QualityResult | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [assessing, setAssessing] = useState(false);

  useEffect(() => {
    apiClient.get("/api/ad-units").then((r) => { setAdUnits(r.data); if (r.data.length > 0) setSelectedUnit(r.data[0].id); }).catch(() => {});
  }, []);

  const assessTraffic = async () => {
    if (!selectedUnit) return;
    setAssessing(true);
    try {
      const [q, t, a] = await Promise.all([
        apiClient.post(`/api/traffic/assess/${selectedUnit}`),
        apiClient.get(`/api/traffic/ad-unit/${selectedUnit}/trend`),
        apiClient.get(`/api/traffic/ad-unit/${selectedUnit}/alerts`),
      ]);
      setQuality(q.data);
      setTrend(t.data.points || []);
      setAlerts(a.data || []);
    } catch (e) { console.error(e); }
    setAssessing(false);
  };

  useEffect(() => { if (selectedUnit) assessTraffic(); }, [selectedUnit]);

  const gc = gradeConfig[quality?.grade || ""] || gradeConfig.standard;
  const GradeIcon = gc.icon;

  const subScores = quality ? [
    { label: "CTR " + "评分", value: quality.ctr_score, max: 100 },
    { label: "CVR " + "评分", value: quality.cvr_score, max: 100 },
    { label: "跳出评分", value: quality.bounce_score, max: 100 },
    { label: "停留评分", value: quality.dwell_score, max: 100 },
    { label: "交互评分", value: quality.interaction_score, max: 100 },
  ] : [];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">流量质量</h1>
          <p className="text-sm text-slate-400 mt-1">监控广告位流量质量和作弊检测</p>
        </div>
      </header>

      <div className="card p-4 flex items-center gap-4">
        <label className="text-sm text-slate-400">广告位：</label>
        <select value={selectedUnit} onChange={(e) => setSelectedUnit(e.target.value)}
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100">
          {adUnits.map((au) => <option key={au.id} value={au.id}>{au.name} ({au.ad_format})</option>)}
        </select>
        <button onClick={assessTraffic} disabled={assessing} className="btn-primary text-sm flex items-center gap-2">
          {assessing ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
          立即评估
        </button>
      </div>

      {quality && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={cn("card p-5 flex items-center gap-4", gc.bg)}>
              <GradeIcon size={36} className={gc.color} />
              <div>
                <div className="text-sm text-slate-400">流量等级</div>
                <div className={cn("text-xl font-bold", gc.color)}>{gc.label}</div>
                <div className="text-xs text-slate-500">评分：{quality.quality_score}/100</div>
              </div>
            </div>
            <div className="card p-5">
              <div className="text-sm text-slate-400 mb-1">事件（24h）</div>
              <div className="flex gap-4 text-sm">
                <span>{quality.impressions.toLocaleString()} 展示</span>
                <span className="text-green-400">{quality.clicks} 点击</span>
                <span className="text-amber-400">{quality.conversions} 转化</span>
              </div>
            </div>
            <div className="card p-5">
              <div className="text-sm text-slate-400 mb-1">标记</div>
              {quality.flags.length === 0 ? (
                <span className="text-green-400 text-sm">未检测到异常</span>
              ) : (
                <div className="flex flex-wrap gap-1">
                  {quality.flags.map((f) => (
                    <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-red-500/10 text-red-400">{f}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-medium text-slate-300 mb-4">评分明细</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {subScores.map((s) => (
                <div key={s.label} className="text-center">
                  <div className="text-2xl font-bold text-slate-100">{s.value.toFixed(0)}</div>
                  <div className="text-xs text-slate-500 mt-1">{s.label}</div>
                  <div className="w-full bg-slate-700 rounded-full h-1.5 mt-2">
                    <div className={cn("h-1.5 rounded-full", s.value >= 80 ? "bg-green-500" : s.value >= 60 ? "bg-amber-500" : "bg-red-500")}
                      style={{ width: `${(s.value / s.max) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {trend.length > 0 && (
            <div className="card p-6">
              <h3 className="text-sm font-medium text-slate-300 mb-4">
                <TrendingUp size={16} className="inline mr-2" />质量趋势
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis domain={[0, 100]} stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "8px" }} />
                  <Bar dataKey="quality_score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="card p-6">
            <h3 className="text-sm font-medium text-slate-300 mb-4">
              <ShieldAlert size={16} className="inline mr-2" />作弊告警
            </h3>
            {alerts.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <ShieldCheck size={40} className="mx-auto mb-2 text-green-500/50" />
                <p className="text-sm">该广告位暂无作弊告警</p>
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.map((a) => (
                  <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50">
                    <div className={cn("p-1.5 rounded-full mt-0.5", a.severity === "critical" ? "bg-red-500/10" : "bg-amber-500/10")}>
                      {a.severity === "critical" ? <ShieldAlert size={14} className="text-red-400" /> : <AlertTriangle size={14} className="text-amber-400" />}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-slate-200">{a.alert_type}</span>
                        <span className={cn("text-xs px-1.5 py-0.5 rounded", a.severity === "critical" ? "bg-red-500/10 text-red-400" : "bg-amber-500/10 text-amber-400")}>{a.severity}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{a.description}</p>
                      <span className="text-xs text-slate-600 mt-1 block">{new Date(a.detected_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
export default TrafficQuality;