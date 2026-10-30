import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api';
import { ProviderConfig } from '../../lib/types';
import {
  LayoutDashboard,
  Code2,
  Mic,
  Calendar,
  TrendingUp,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Command,
  Sparkles,
  BookOpen,
  Boxes,
} from 'lucide-react';

interface SidebarProps {
  onOpenCommandPalette: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenCommandPalette,
  isCollapsed: controlledCollapsed,
  onToggleCollapse,
}) => {
  const [internalCollapsed, setInternalCollapsed] = useState(() => {
    return localStorage.getItem('skillissue_sidebar_collapsed') === 'true';
  });

  const isCollapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed;
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleToggle = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setInternalCollapsed((prev) => {
        const next = !prev;
        localStorage.setItem('skillissue_sidebar_collapsed', String(next));
        return next;
      });
    }
  };

  useEffect(() => {
    if (user) {
      api.get<ProviderConfig>('/providers/config')
        .then(setProviderConfig)
        .catch(() => {});
    }
  }, [user, location.pathname]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onOpenCommandPalette();
      } else if ((e.metaKey || e.ctrlKey) && e.key === '1') {
        e.preventDefault();
        navigate('/');
      } else if ((e.metaKey || e.ctrlKey) && e.key === '2') {
        e.preventDefault();
        navigate('/coding');
      } else if ((e.metaKey || e.ctrlKey) && e.key === '3') {
        e.preventDefault();
        navigate('/interviews/new');
      } else if ((e.metaKey || e.ctrlKey) && e.key === '4') {
        e.preventDefault();
        navigate('/planly');
      } else if ((e.metaKey || e.ctrlKey) && e.key === '5') {
        e.preventDefault();
        navigate('/progress');
      } else if ((e.metaKey || e.ctrlKey) && e.key === ',') {
        e.preventDefault();
        navigate('/settings/provider');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, onOpenCommandPalette]);

  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard, shortcut: '⌘1' },
    { label: 'DSA Arena', path: '/coding', icon: Code2, shortcut: '⌘2' },
    { label: 'AI Projects', path: '/projects', icon: Boxes, badge: 'NEW' },
    { label: 'Interview', path: '/interviews/new', icon: Mic, shortcut: '⌘3' },
    { label: 'Planly', path: '/planly', icon: Calendar, shortcut: '⌘4' },
    { label: 'Skills & Data', path: '/progress', icon: TrendingUp, shortcut: '⌘5' },
  ];

  if (!user) return null;

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-40 bg-white border-r border-slate-200/90 flex flex-col transition-all duration-200 select-none shadow-xs ${
        isCollapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-3.5 border-b border-slate-100">
        <Link to="/" className="flex items-center gap-3 overflow-hidden group">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white flex-shrink-0 shadow-sm shadow-indigo-500/25 group-hover:scale-105 transition-transform">
            <Sparkles className="w-4 h-4 fill-white/20" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col truncate">
              <span className="font-bold text-sm tracking-tight text-slate-900">Skill Issue</span>
              <span className="text-[11px] text-slate-500 -mt-0.5 truncate font-medium">Now we have data.</span>
            </div>
          )}
        </Link>

        <button
          onClick={handleToggle}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors flex-shrink-0"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          aria-label="Toggle Sidebar"
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Command Palette Trigger */}
      <div className="p-3">
        <button
          onClick={onOpenCommandPalette}
          className={`w-full flex items-center justify-between py-2 rounded-xl bg-slate-100/70 hover:bg-slate-200/60 text-slate-600 border border-slate-200/70 text-xs font-medium transition-all shadow-2xs ${
            isCollapsed ? 'px-2 justify-center' : 'px-3'
          }`}
          title="Search actions (⌘K)"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Command className="w-3.5 h-3.5 flex-shrink-0 text-slate-500" />
            {!isCollapsed && <span className="truncate">Search actions...</span>}
          </div>
          {!isCollapsed && (
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-white border border-slate-200 rounded-md text-slate-500 font-semibold shadow-2xs">
              ⌘K
            </kbd>
          )}
        </button>
      </div>

      {/* Main Navigation Items */}
      <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                isActive
                  ? 'bg-indigo-50/80 text-indigo-700 font-semibold border border-indigo-200/70 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon
                  className={`w-4 h-4 flex-shrink-0 transition-colors ${
                    isActive ? 'text-indigo-600' : 'text-slate-500 group-hover:text-slate-800'
                  }`}
                />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </div>

              {!isCollapsed && (item as any).badge ? (
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 text-indigo-700 uppercase tracking-wider">
                  {(item as any).badge}
                </span>
              ) : !isCollapsed && item.shortcut ? (
                <span className="text-[11px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
                  {item.shortcut}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Footer Section */}
      <div className="p-3 border-t border-slate-100 space-y-1.5 bg-slate-50/50">
        {/* Model Provider & Usage Status Pill */}
        <Link
          to="/settings/provider"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white text-xs transition-all border border-transparent hover:border-slate-200 hover:shadow-2xs ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="Configure AI Provider & Spending Budget"
        >
          <div
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              providerConfig?.is_valid ? 'bg-emerald-500 ring-2 ring-emerald-500/20' : 'bg-amber-400 ring-2 ring-amber-400/20'
            }`}
          />
          {!isCollapsed && (
            <div className="flex flex-col min-w-0 flex-1">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                <span className="truncate">
                  {providerConfig?.is_valid
                    ? (providerConfig.provider_name === 'azure' ? 'Azure OpenAI' : 'Bedrock BYOC')
                    : 'Setup Required'}
                </span>
                {providerConfig?.estimated_cost_usd !== undefined && (
                  <span className="font-mono text-xs text-emerald-600 font-bold ml-1 shrink-0">
                    ${providerConfig.estimated_cost_usd.toFixed(3)}
                  </span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 truncate font-mono">
                {providerConfig?.total_tokens_used !== undefined
                  ? `${(providerConfig.total_tokens_used / 1000).toFixed(1)}k tokens used`
                  : (providerConfig?.aws_region || 'Configure Keys')}
              </span>
            </div>
          )}
        </Link>

        {/* AWS Setup Docs */}
        <Link
          to="/docs/aws-bedrock-setup"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-white text-xs font-medium transition-all hover:shadow-2xs ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="AWS Bedrock Setup Guide"
        >
          <BookOpen className="w-4 h-4 flex-shrink-0 text-slate-500" />
          {!isCollapsed && <span className="truncate">Bedrock Guide</span>}
        </Link>

        {/* Settings */}
        <Link
          to="/settings/provider"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-white text-xs font-medium transition-all hover:shadow-2xs ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="Settings (⌘,)"
        >
          <Settings className="w-4 h-4 flex-shrink-0 text-slate-500" />
          {!isCollapsed && <span className="truncate">Settings</span>}
        </Link>

        {/* User Account / Sign Out */}
        <div className="pt-1 border-t border-slate-200/60">
          <button
            onClick={logout}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-rose-600 hover:bg-rose-50 text-xs font-medium transition-colors ${
              isCollapsed ? 'justify-center' : ''
            }`}
            title="Sign out of account"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && <span>Sign Out</span>}
          </button>
        </div>
      </div>
    </aside>
  );
};
