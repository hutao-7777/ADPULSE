import { useState } from 'react';
import { NavLink, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Gavel,
  GitBranch,
  FlaskConical,
  BrainCircuit,
  KeyRound,
  LogOut,
  User,
  ChevronDown,
  Database,
} from 'lucide-react';
import { cn } from '../utils/cn';
import useAuthStore from '../stores/authStore';

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
}

const navItems: NavItem[] = [
  { path: '/dashboard', label: '数据看板', icon: LayoutDashboard },
  { path: '/rtb', label: 'RTB 竞价引擎', icon: Gavel },
  { path: '/attribution', label: '归因 & 流量', icon: GitBranch },
  { path: '/abtesting', label: 'A/B 测试', icon: FlaskConical },
  { path: '/agent', label: '智能 Agent', icon: BrainCircuit },
  { path: '/ipinyou', label: 'iPinYou 数据', icon: Database },
  { path: '/api-keys', label: 'API Keys', icon: KeyRound },
];

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen w-full bg-primary">
      {/* 侧边栏 */}
      <aside className="w-16 flex-shrink-0 bg-secondary border-r border-slate-700/50 flex flex-col items-center py-4 z-20">
        <div className="mb-6">
          <Link to="/">
            <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-blue-500/20">
              <span className="text-white font-bold text-lg">A</span>
            </div>
          </Link>
        </div>

        <nav className="flex-1 flex flex-col gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={cn(
                  'group relative w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200',
                  isActive
                    ? 'bg-accent/15 text-accent shadow-[0_0_12px_rgba(59,130,246,0.25)]'
                    : 'text-muted hover:text-slate-100 hover:bg-slate-700/50'
                )}
                aria-label={item.label}
              >
                <Icon size={22} strokeWidth={isActive ? 2.2 : 1.8} />

                {/* 工具提示 */}
                <span className="absolute left-14 bg-secondary text-slate-100 text-xs px-2 py-1 rounded-md border border-slate-700 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 shadow-xl">
                  {item.label}
                </span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部导航 */}
        <header className="h-16 bg-secondary/50 border-b border-slate-700/50 flex items-center justify-between px-6">
          <div className="flex items-center gap-6">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'hidden md:flex items-center gap-2 text-sm transition-colors',
                    isActive ? 'text-accent' : 'text-muted hover:text-slate-100'
                  )}
                >
                  <Icon size={16} />
                  {item.label}
                </NavLink>
              );
            })}
          </div>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setMenuOpen((v) => !v)}
                  className="flex items-center gap-2 text-slate-300 hover:text-slate-100 px-3 py-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
                >
                  <User size={18} />
                  <span className="text-sm max-w-[160px] truncate">
                    {user?.email || '用户'}
                  </span>
                  <ChevronDown size={14} />
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-secondary border border-slate-700/50 rounded-xl shadow-2xl py-1 z-50">
                    <Link
                      to="/api-keys"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-slate-300 hover:text-slate-100 hover:bg-slate-700/50"
                    >
                      <KeyRound size={16} />
                      API Keys
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2 text-sm text-danger hover:bg-danger/10"
                    >
                      <LogOut size={16} />
                      退出登录
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-sm text-slate-300 hover:text-slate-100 px-3 py-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
                >
                  登录
                </Link>
                <Link
                  to="/register"
                  className="text-sm bg-accent hover:bg-blue-600 text-white px-4 py-1.5 rounded-lg transition-colors"
                >
                  注册
                </Link>
              </>
            )}
          </div>
        </header>

        <main className="flex-1 min-w-0 overflow-auto">
          <div className="min-h-full p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default Layout;
