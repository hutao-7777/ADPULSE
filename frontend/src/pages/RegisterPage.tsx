import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Mail, Lock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import useAuthStore from '../stores/authStore';

function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const validation = useMemo(() => {
    return {
      length: password.length >= 8,
      hasLetter: /[a-zA-Z]/.test(password),
      hasNumber: /\d/.test(password),
      match: password === confirmPassword && confirmPassword.length > 0,
    };
  }, [password, confirmPassword]);

  const isValid =
    validation.length && validation.hasLetter && validation.hasNumber && validation.match;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    setLoading(true);
    try {
      await register(email, password);
      toast.success('注册成功');
      navigate('/dashboard');
    } catch {
      toast.error('注册失败，请检查邮箱是否已被注册');
    } finally {
      setLoading(false);
    }
  };

  const Rule = ({
    label,
    satisfied,
  }: {
    label: string;
    satisfied: boolean;
  }) => (
    <li className="flex items-center gap-2 text-sm">
      {satisfied ? (
        <CheckCircle size={14} className="text-success" />
      ) : (
        <XCircle size={14} className="text-danger" />
      )}
      <span className={satisfied ? 'text-slate-300' : 'text-muted'}>{label}</span>
    </li>
  );

  return (
    <div className="min-h-screen flex items-center justify-center bg-primary px-4">
      <div className="w-full max-w-md bg-secondary rounded-2xl border border-slate-700/50 p-8 shadow-2xl">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-xl bg-accent flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/20">
            <span className="text-white font-bold text-2xl">A</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">创建 AdPulse 账号</h1>
          <p className="text-muted mt-2">开始搭建你的程序化广告平台</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">邮箱</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-primary border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
                placeholder="you@example.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">密码</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-primary border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">确认密码</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full bg-primary border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
                placeholder="••••••••"
              />
            </div>
          </div>

          <ul className="space-y-1.5 bg-primary/50 rounded-lg p-3 border border-slate-700/50">
            <Rule label="至少 8 位" satisfied={validation.length} />
            <Rule label="包含字母" satisfied={validation.hasLetter} />
            <Rule label="包含数字" satisfied={validation.hasNumber} />
            <Rule label="两次密码一致" satisfied={validation.match} />
          </ul>

          <button
            type="submit"
            disabled={!isValid || loading}
            className="w-full bg-accent hover:bg-blue-600 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
          >
            {loading && <Loader2 className="animate-spin" size={18} />}
            注册
          </button>
        </form>

        <p className="text-center text-sm text-muted mt-6">
          已有账号？{' '}
          <Link to="/login" className="text-accent hover:underline">
            去登录
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
