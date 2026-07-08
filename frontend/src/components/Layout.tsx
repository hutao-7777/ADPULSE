import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Gavel,
  GitBranch,
  FlaskConical,
  BrainCircuit,
} from 'lucide-react';
import { cn } from '../utils/cn';

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
];

interface LayoutProps {
  children: React.ReactNode;
}

function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="flex h-screen w-full bg-primary">
      {/* 侧边栏 */}
      <aside className="w-16 flex-shrink-0 bg-secondary border-r border-slate-700/50 flex flex-col items-center py-4 z-20">
        <div className="mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-bold text-lg">A</span>
          </div>
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
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="min-h-full p-6">{children}</div>
      </main>
    </div>
  );
}

export default Layout;
