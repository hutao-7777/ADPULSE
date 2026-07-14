import { useEffect, useState } from "react";
import { Building2, Plus, Smartphone, Loader2, X, ChevronDown, ChevronRight } from "lucide-react";
import apiClient from "../lib/apiClient";
import toast from "react-hot-toast";
import { cn } from "../utils/cn";

interface Publisher { id: string; name: string; company: string | null; email: string | null; website: string | null; status: string; created_at: string; }
interface App { id: string; publisher_id: string; name: string; platform: string; domain: string | null; status: string; }

function PublishersPage() {
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [apps, setApps] = useState<Record<string, App[]>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newPub, setNewPub] = useState({ name: "", company: "", email: "" });
  const [showAppModal, setShowAppModal] = useState<string | null>(null);
  const [newApp, setNewApp] = useState({ name: "", platform: "web", domain: "" });

  const fetchPublishers = () => {
    apiClient.get("/api/publishers").then((r) => setPublishers(r.data)).catch(() => {}).finally(() => setLoading(false));
  };
  useEffect(() => { fetchPublishers(); }, []);

  const fetchApps = async (pubId: string) => {
    if (apps[pubId]) return;
    const r = await apiClient.get(`/api/publishers/${pubId}/apps`);
    setApps((prev) => ({ ...prev, [pubId]: r.data }));
  };

  const createPublisher = async () => {
    await apiClient.post("/api/publishers", newPub);
    toast.success("创建成功"); setShowModal(false);
    setNewPub({ name: "", company: "", email: "" }); fetchPublishers();
  };

  const createApp = async (pubId: string) => {
    await apiClient.post(`/api/publishers/${pubId}/apps`, newApp);
    toast.success("创建成功"); setShowAppModal(null);
    setNewApp({ name: "", platform: "web", domain: "" });
    setApps((p) => { const n = { ...p }; delete n[pubId]; return n; });
    fetchApps(pubId);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="animate-spin w-8 h-8 text-accent" /></div>;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-slate-100">媒体主</h1><p className="text-sm text-slate-400 mt-1">管理您的媒体主和应用</p></div>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2"><Plus size={16} /> 添加媒体主</button>
      </header>

      {publishers.length === 0 ? (
        <div className="card p-12 text-center text-slate-500"><Building2 size={48} className="mx-auto mb-4 opacity-50" /><p>暂无媒体主</p></div>
      ) : (
        <div className="space-y-3">{publishers.map((pub) => (
          <div key={pub.id} className="card overflow-hidden">
            <button onClick={() => { setExpanded((p) => ({ ...p, [pub.id]: !p[pub.id] })); fetchApps(pub.id); }}
              className="w-full flex items-center justify-between p-5 hover:bg-slate-700/20 transition-colors">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10"><Building2 size={20} className="text-blue-400" /></div>
                <div className="text-left"><div className="font-medium text-slate-100">{pub.name}</div><div className="text-xs text-slate-500">{pub.company || pub.email || ""}</div></div>
              </div>
              <div className="flex items-center gap-3">
                <span className={cn("text-xs px-2 py-0.5 rounded-full", pub.status === "active" ? "bg-green-500/10 text-green-400" : "bg-slate-500/10 text-slate-400")}>{pub.status}</span>
                {expanded[pub.id] ? <ChevronDown size={18} className="text-slate-400" /> : <ChevronRight size={18} className="text-slate-400" />}
              </div>
            </button>
            {expanded[pub.id] && (
              <div className="border-t border-slate-700/50 px-5 py-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm text-slate-400">应用</span>
                  <button onClick={() => setShowAppModal(pub.id)} className="text-xs text-accent hover:text-blue-400 flex items-center gap-1"><Plus size={14} /> 添加应用</button>
                </div>
                {(apps[pub.id] || []).length === 0 ? <p className="text-xs text-slate-500">暂无应用</p> : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {apps[pub.id].map((app) => (
                      <div key={app.id} className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50">
                        <Smartphone size={16} className="text-slate-400" />
                        <div><div className="text-sm text-slate-200">{app.name}</div><div className="text-xs text-slate-500">{app.platform}{app.domain ? " - " + app.domain : ""}</div></div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}</div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-secondary border border-slate-700/50 rounded-xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4"><h2 className="text-lg font-semibold text-slate-100">新建媒体主</h2><button onClick={() => setShowModal(false)}><X size={20} className="text-slate-400" /></button></div>
            <div className="space-y-3">
              <input placeholder="名称 *" value={newPub.name} onChange={(e) => setNewPub((p) => ({ ...p, name: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <input placeholder="公司" value={newPub.company} onChange={(e) => setNewPub((p) => ({ ...p, company: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <input placeholder="邮箱" value={newPub.email} onChange={(e) => setNewPub((p) => ({ ...p, email: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <button onClick={createPublisher} className="w-full btn-primary mt-2">创建</button>
            </div>
          </div>
        </div>
      )}

      {showAppModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowAppModal(null)}>
          <div className="bg-secondary border border-slate-700/50 rounded-xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4"><h2 className="text-lg font-semibold text-slate-100">新建应用</h2><button onClick={() => setShowAppModal(null)}><X size={20} className="text-slate-400" /></button></div>
            <div className="space-y-3">
              <input placeholder="名称 *" value={newApp.name} onChange={(e) => setNewApp((a) => ({ ...a, name: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100" />
              <select value={newApp.platform} onChange={(e) => setNewApp((a) => ({ ...a, platform: e.target.value }))} className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100">
                <option value="web">Web</option><option value="android">Android</option><option value="ios">iOS</option>
              </select>
              <button onClick={() => showAppModal && createApp(showAppModal)} className="w-full btn-primary mt-2">创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default PublishersPage;