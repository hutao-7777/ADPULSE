import { useEffect, useState } from "react";
import { Layers, Plus, Loader2, Zap, X, ChevronDown, ChevronRight, GripVertical, Save, Trash2, Pencil } from "lucide-react";
import apiClient from "../lib/apiClient";
import toast from "react-hot-toast";
import { cn } from "../utils/cn";

interface AdUnit { id: string; app_id: string; name: string; ad_format: string; width: number | null; height: number | null; status: string; waterfall_config: any; bidding_config: any; created_at: string; }
interface AdSource { id: string; ad_unit_id: string; ad_network_id: string; instance_name: string; ecpm: number; priority: number; bidding_endpoint: string | null; status: string; }
interface AdNetwork { id: string; name: string; display_name: string | null; supports_bidding: boolean; }
interface App { id: string; publisher_id: string; name: string; platform: string; }

const formatLabels: Record<string, string> = { banner: "横幅", interstitial: "插屏", rewarded: "激励视频", native: "原生" };

function AdUnitsPage() {
  const [adUnits, setAdUnits] = useState<AdUnit[]>([]);
  const [sources, setSources] = useState<Record<string, AdSource[]>>({});
  const [networks, setNetworks] = useState<AdNetwork[]>([]);
  const [apps, setApps] = useState<App[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newUnit, setNewUnit] = useState({ app_id: "", name: "", ad_format: "banner" });
  const [showSourceModal, setShowSourceModal] = useState<string | null>(null);
  const [newSource, setNewSource] = useState({ ad_network_id: "", instance_name: "", ecpm: 0 });

  useEffect(() => {
    apiClient.get("/api/publishers").then((r) => {
      return Promise.all(r.data.map((p: any) => apiClient.get(`/api/publishers/${p.id}/apps`).then((a) => a.data)));
    }).then((allApps) => setApps(allApps.flat())).catch(() => {});
    apiClient.get("/api/ad-units").then((r) => setAdUnits(r.data)).catch(() => {}).finally(() => setLoading(false));
    apiClient.get("/api/ad-units/ad-networks").then((r) => setNetworks(r.data)).catch(() => {});
  }, []);

  const fetchSources = async (auId: string) => {
    if (sources[auId]) return;
    const r = await apiClient.get(`/api/ad-units/${auId}/sources`);
    setSources((p) => ({ ...p, [auId]: r.data }));
  };

  const createAdUnit = async () => {
    await apiClient.post("/api/ad-units", newUnit);
    toast.success("Created"); setShowModal(false);
    setNewUnit({ app_id: "", name: "", ad_format: "banner" });
    apiClient.get("/api/ad-units").then((r) => setAdUnits(r.data));
  };

  const addSource = async (auId: string) => {
    await apiClient.post(`/api/ad-units/${auId}/sources`, { ...newSource, priority: 0, credentials: {} });
    toast.success("Added"); setShowSourceModal(null);
    setNewSource({ ad_network_id: "", instance_name: "", ecpm: 0 });
    setSources((p) => { const n = { ...p }; delete n[auId]; return n; });
    fetchSources(auId);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="animate-spin w-8 h-8 text-accent" /></div>;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-slate-100">广告位</h1><p className="text-sm text-slate-400 mt-1">管理广告位和 Mediation 配置</p></div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> 添加广告位</button>
      </header>
      {adUnits.length === 0 ? (
        <div className="card p-12 text-center text-slate-500"><Layers size={48} className="mx-auto mb-4 opacity-50" /><p>暂无广告位</p></div>
      ) : (
        <div className="space-y-3">{adUnits.map((au) => {
          const srcs = sources[au.id] || [];
          const waterfall = srcs.filter((s) => !s.bidding_endpoint);
          const bidding = srcs.filter((s) => s.bidding_endpoint);
          return (
          <div key={au.id} className="card overflow-hidden">
            <button onClick={() => { setExpanded((p) => ({ ...p, [au.id]: !p[au.id] })); fetchSources(au.id); }}
              className="w-full flex items-center justify-between p-5 hover:bg-slate-700/20 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10"><Zap size={20} className="text-purple-400" /></div>
                <div className="text-left"><div className="font-medium text-slate-100">{au.name}</div><div className="text-xs text-slate-500">{formatLabels[au.ad_format] || au.ad_format}</div></div>
              </div>
              <div className="flex items-center gap-3">
                {au.width && au.height ? <span className="text-xs text-slate-500">{au.width}x{au.height}</span> : null}
                <span className={cn("text-xs px-2 py-0.5 rounded-full", au.status === "active" ? "bg-green-500/10 text-green-400" : "bg-slate-500/10 text-slate-400")}>{au.status}</span>
                {expanded[au.id] ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
              </div>
            </button>
            {expanded[au.id] && (
              <div className="border-t border-slate-700/50 px-5 py-4 space-y-3">
                <div className="flex items-center justify-between"><span className="text-sm text-slate-400">广告源</span>
                  <button onClick={() => setShowSourceModal(au.id)} className="text-xs text-accent flex items-center gap-1"><Plus size={14} /> 添加广告源</button>
                </div>
                {srcs.length === 0 ? <p className="text-xs text-slate-500">No sources configured</p> : (
                  <div className="overflow-hidden rounded-lg border border-slate-700/50">
                    <table className="w-full text-sm">
                      <thead><tr className="text-left text-xs text-slate-500 bg-slate-800/50"><th className="p-2">Network</th><th className="p-2">eCPM</th><th className="p-2">Type</th><th className="p-2">Status</th></tr></thead>
                      <tbody className="text-slate-300">{srcs.map((s) => (
                        <tr key={s.id} className="border-t border-slate-700/30">
                          <td className="p-2">{s.instance_name}</td>
                          <td className="p-2">${s.ecpm.toFixed(2)}</td>
                          <td className="p-2"><span className={cn("text-xs px-1.5 py-0.5 rounded-full", s.bidding_endpoint ? "bg-blue-500/10 text-blue-400" : "bg-slate-500/10 text-slate-400")}>{s.bidding_endpoint ? "竞价" : "排序"}</span></td>
                          <td className="p-2"><span className={cn("text-xs px-1.5 py-0.5 rounded-full", s.status === "active" ? "bg-green-500/10 text-green-400" : "bg-slate-500/10 text-slate-400")}>{s.status}</span></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )})}</div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-secondary border border-slate-700/50 rounded-xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-slate-100 mb-4">新建广告位</h2>
            <div className="space-y-3">
              <select value={newUnit.app_id} onChange={(e) => setNewUnit((u) => ({ ...u, app_id: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="">选择应用</option>
                {apps.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
              <input placeholder="Name" value={newUnit.name} onChange={(e) => setNewUnit((u) => ({ ...u, name: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <select value={newUnit.ad_format} onChange={(e) => setNewUnit((u) => ({ ...u, ad_format: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="banner">Banner</option><option value="interstitial">Interstitial</option><option value="rewarded">Rewarded</option><option value="native">Native</option>
              </select>
              <button onClick={createAdUnit} className="w-full btn-primary mt-2">创建</button>
            </div>
          </div>
        </div>
      )}

      {showSourceModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowSourceModal(null)}>
          <div className="bg-secondary border border-slate-700/50 rounded-xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-slate-100 mb-4">添加广告源</h2>
            <div className="space-y-3">
              <select value={newSource.ad_network_id} onChange={(e) => setNewSource((s) => ({ ...s, ad_network_id: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="">选择广告网络</option>
                {networks.map((n) => <option key={n.id} value={n.id}>{n.display_name || n.name}</option>)}
              </select>
              <input placeholder="Instance Name" value={newSource.instance_name} onChange={(e) => setNewSource((s) => ({ ...s, instance_name: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <input placeholder="eCPM" type="number" step="0.01" value={newSource.ecpm} onChange={(e) => setNewSource((s) => ({ ...s, ecpm: parseFloat(e.target.value) || 0 }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <button onClick={() => showSourceModal && addSource(showSourceModal)} className="w-full btn-primary mt-2">添加</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default AdUnitsPage;