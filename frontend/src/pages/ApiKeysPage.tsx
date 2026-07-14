import { useEffect, useState } from 'react';

import toast from 'react-hot-toast';

import { Copy, KeyRound, Loader2, Plus, Trash2, X } from 'lucide-react';

import useAuthStore, { ApiKey } from '../stores/authStore';



function ApiKeysPage() {

  const { apiKeys, fetchApiKeys, createApiKey, revokeApiKey } = useAuthStore();

  const [loading, setLoading] = useState(true);

  const [modalOpen, setModalOpen] = useState(false);

  const [newKeyName, setNewKeyName] = useState('');

  const [creating, setCreating] = useState(false);

  const [createdKey, setCreatedKey] = useState<{ key: string; record: ApiKey } | null>(null);



  useEffect(() => {

    fetchApiKeys().finally(() => setLoading(false));

  }, [fetchApiKeys]);



  const handleCreate = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!newKeyName.trim()) return;

    setCreating(true);

    try {

      const result = await createApiKey(newKeyName.trim());

      setCreatedKey(result);

      setNewKeyName('');

      toast.success('API Key 创建成功');

    } catch {

      toast.error('创建失败');

    } finally {

      setCreating(false);

    }

  };



  const handleRevoke = async (id: string, name: string) => {

    if (!window.confirm(`确定要撤销 API Key "${name}" 吗？`)) return;

    try {

      await revokeApiKey(id);

      toast.success('已撤销');

    } catch {

      toast.error('撤销失败');

    }

  };



  const copyToClipboard = (text: string) => {

    navigator.clipboard.writeText(text);

    toast.success('已复制到剪贴板');

  };



  const closeModal = () => {

    setModalOpen(false);

    setCreatedKey(null);

    setNewKeyName('');

  };



  return (

    <div className="space-y-6">

      <div className="flex items-center justify-between">

        <div>

          <h1 className="text-2xl font-bold text-slate-100">API 密钥</h1>

          <p className="text-muted mt-1">管理用于 DSP/RTB 集成的 API Key</p>

        </div>

        <button

          onClick={() => setModalOpen(true)}

          className="bg-accent hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"

        >

          <Plus size={18} />

          新增 API Key

        </button>

      </div>



      {loading ? (

        <div className="flex items-center justify-center h-64 text-muted">

          <Loader2 className="animate-spin mr-2" />

          加载中...

        </div>

      ) : apiKeys.length === 0 ? (

        <div className="bg-secondary border border-slate-700/50 rounded-xl p-10 text-center text-muted">

          <KeyRound className="mx-auto mb-3" size={40} />

          暂无 API Key

        </div>

      ) : (

        <div className="bg-secondary border border-slate-700/50 rounded-xl overflow-hidden">

          <table className="w-full text-left text-sm">

            <thead className="bg-primary/50 text-slate-300 uppercase text-xs">

              <tr>

                <th className="px-6 py-3">名称</th>

                <th className="px-6 py-3">Prefix</th>

                <th className="px-6 py-3">创建时间</th>

                <th className="px-6 py-3">状态</th>

                <th className="px-6 py-3 text-right">操作</th>

              </tr>

            </thead>

            <tbody className="divide-y divide-slate-700/50">

              {apiKeys.map((key) => (

                <tr key={key.id} className="hover:bg-primary/30 transition-colors">

                  <td className="px-6 py-4 text-slate-100 font-medium">{key.name}</td>

                  <td className="px-6 py-4 text-slate-300 font-mono">{key.key_prefix}...</td>

                  <td className="px-6 py-4 text-slate-400">

                    {new Date(key.created_at).toLocaleString()}

                  </td>

                  <td className="px-6 py-4">

                    <span

                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${

                        key.is_active

                          ? 'bg-success/15 text-success'

                          : 'bg-danger/15 text-danger'

                      }`}

                    >

                      {key.is_active ? '活跃' : '已撤销'}

                    </span>

                  </td>

                  <td className="px-6 py-4 text-right">

                    {key.is_active && (

                      <button

                        onClick={() => handleRevoke(key.id, key.name)}

                        className="text-danger hover:text-red-400 inline-flex items-center gap-1 transition-colors"

                      >

                        <Trash2 size={16} />

                        撤销

                      </button>

                    )}

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      )}



      {modalOpen && (

        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">

          <div className="bg-secondary border border-slate-700/50 rounded-2xl w-full max-w-lg p-6 shadow-2xl">

            <div className="flex items-center justify-between mb-5">

              <h2 className="text-xl font-bold text-slate-100">新增 API Key</h2>

              <button onClick={closeModal} className="text-muted hover:text-slate-100">

                <X size={20} />

              </button>

            </div>



            {createdKey ? (

              <div className="space-y-4">

                <div className="bg-success/10 border border-success/30 rounded-lg p-4">

                  <p className="text-sm text-success mb-2">API Key 已生成，请立即复制，只显示一次：</p>

                  <div className="flex items-center gap-2">

                    <code className="flex-1 bg-primary rounded px-3 py-2 text-slate-100 text-sm break-all">

                      {createdKey.key}

                    </code>

                    <button

                      onClick={() => copyToClipboard(createdKey.key)}

                      className="bg-primary hover:bg-slate-700 text-slate-100 p-2 rounded-lg transition-colors"

                      title="复制"

                    >

                      <Copy size={18} />

                    </button>

                  </div>

                </div>

                <button

                  onClick={closeModal}

                  className="w-full bg-accent hover:bg-blue-600 text-white py-2.5 rounded-lg transition-colors"

                >

                  完成

                </button>

              </div>

            ) : (

              <form onSubmit={handleCreate} className="space-y-4">

                <div>

                  <label className="block text-sm font-medium text-slate-300 mb-1.5">

                    Key 名称

                  </label>

                  <input

                    type="text"

                    value={newKeyName}

                    onChange={(e) => setNewKeyName(e.target.value)}

                    required

                    className="w-full bg-primary border border-slate-700 rounded-lg py-2.5 px-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"

                    placeholder="例如：DSP-Production"

                  />

                </div>

                <div className="flex justify-end gap-3 pt-2">

                  <button

                    type="button"

                    onClick={closeModal}

                    className="px-4 py-2 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"

                  >

                    取消

                  </button>

                  <button

                    type="submit"

                    disabled={creating}

                    className="px-4 py-2 rounded-lg bg-accent hover:bg-blue-600 text-white flex items-center gap-2 transition-colors disabled:opacity-60"

                  >

                    {creating && <Loader2 className="animate-spin" size={18} />}

                    创建

                  </button>

                </div>

              </form>

            )}

          </div>

        </div>

      )}

    </div>

  );

}



export default ApiKeysPage;
