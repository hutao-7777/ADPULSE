import { Link } from 'react-router-dom';
import { BarChart3, Shield, Zap } from 'lucide-react';

function LandingPage() {
  return (
    <div className="min-h-screen bg-primary">
      <nav className="border-b border-slate-700/50 bg-secondary/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent flex items-center justify-center">
              <span className="text-white font-bold">A</span>
            </div>
            <span className="text-xl font-bold text-slate-100">AdPulse</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/login"
              className="px-4 py-2 rounded-lg text-slate-300 hover:text-slate-100 hover:bg-slate-700/50 transition-colors"
            >
              登录
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 rounded-lg bg-accent hover:bg-blue-600 text-white transition-colors"
            >
              注册
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h1 className="text-5xl font-bold text-slate-100 mb-6">
            程序化广告投放仿真平台
          </h1>
          <p className="text-lg text-muted mb-8">
            RTB 竞价、A/B 测试、多触点归因、AI Agent —— 全链路广告技术栈演练
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/register"
              className="px-6 py-3 rounded-xl bg-accent hover:bg-blue-600 text-white font-medium transition-colors"
            >
              免费开始
            </Link>
            <Link
              to="/login"
              className="px-6 py-3 rounded-xl border border-slate-700 text-slate-300 hover:text-slate-100 hover:border-slate-500 transition-colors"
            >
              已有账号登录
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={Zap}
            title="RTB 实时竞价"
            desc="模拟二价拍卖、DSP 出价策略与竞价延迟优化。"
          />
          <FeatureCard
            icon={BarChart3}
            title="A/B 测试与归因"
            desc="一致性哈希分流、统计检验、Shapley 多触点归因。"
          />
          <FeatureCard
            icon={Shield}
            title="权限与 API Key"
            desc="JWT 认证、RBAC 权限、API Key 管理，安全接入 DSP。"
          />
        </div>
      </main>
    </div>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
}) {
  return (
    <div className="bg-secondary border border-slate-700/50 rounded-2xl p-6 hover:border-accent/30 transition-colors">
      <div className="w-11 h-11 rounded-lg bg-accent/15 text-accent flex items-center justify-center mb-4">
        <Icon size={22} />
      </div>
      <h3 className="text-lg font-semibold text-slate-100 mb-2">{title}</h3>
      <p className="text-muted text-sm leading-relaxed">{desc}</p>
    </div>
  );
}

export default LandingPage;
