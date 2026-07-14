import { useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Building2, Layers, Shield, KeyRound, Menu, X } from "lucide-react";
import { cn } from "../utils/cn";

const navItems = [
  { path: "/dashboard", label: "仪表盘", icon: LayoutDashboard },
  { path: "/publishers", label: "媒体主", icon: Building2 },
  { path: "/ad-units", label: "广告位", icon: Layers },
  { path: "/traffic", label: "流量质量", icon: Shield },
  { path: "/api-keys", label: "API 密钥", icon: KeyRound },
];

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-primary">
      {/* 移动端遮罩 */}
      {sidebarOpen && <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />}

      {/* 侧边栏 */}
      <aside className={cn(
        "fixed md:static inset-y-0 left-0 z-40 w-16 flex-shrink-0 bg-secondary border-r border-slate-700/50 flex flex-col items-center py-4 transition-transform",
        sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        <Link to="/dashboard" className="mb-6">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-bold text-lg">A</span>
          </div>
        </Link>

        <nav className="flex-1 flex flex-col gap-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink key={item.path} to={item.path}
                className={cn(
                  "group relative w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200",
                  isActive
                    ? "bg-accent/15 text-accent shadow-[0_0_12px_rgba(59,130,246,0.25)]"
                    : "text-muted hover:text-slate-100 hover:bg-slate-700/50"
                )} aria-label={item.label}>
                <Icon size={22} strokeWidth={isActive ? 2.2 : 1.8} />
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
        <header className="h-14 bg-secondary/50 border-b border-slate-700/50 flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-2 md:gap-6">
            <button className="md:hidden text-slate-400 hover:text-slate-100" onClick={() => setSidebarOpen((v) => !v)}>
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <NavLink key={item.path} to={item.path}
                  className={cn(
                    "hidden md:flex items-center gap-2 text-sm transition-colors",
                    isActive ? "text-accent" : "text-muted hover:text-slate-100"
                  )}>
                  <Icon size={16} /> {item.label}
                </NavLink>
              );
            })}
          </div>
        </header>

        <main className="flex-1 min-w-0 overflow-auto">
          <div className="min-h-full p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
export default Layout;
