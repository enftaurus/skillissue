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
} from 'lucide-react';


interface SidebarProps {
  onOpenCommandPalette: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenCommandPalette }) => {
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem('skillissue_sidebar_collapsed') === 'true';
  });
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  useEffect(() => {
    localStorage.setItem('skillissue_sidebar_collapsed', String(isCollapsed));
  }, [isCollapsed]);

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
    { label: 'Interview', path: '/interviews/new', icon: Mic, shortcut: '⌘3' },
    { label: 'Planly', path: '/planly', icon: Calendar, shortcut: '⌘4' },
    { label: 'Skills & Data', path: '/progress', icon: TrendingUp, shortcut: '⌘5' },
  ];

  if (!user) return null;

  return (
    <aside
      className={`fixed top-0 left-0 bottom-0 z-40 bg-white border-r border-surface-border flex flex-col transition-all duration-200 select-none ${
        isCollapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-3.5 border-b border-surface-border">
        <Link to="/" className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-lime-500/15 border border-lime-500/30 flex items-center justify-center text-lime-700 flex-shrink-0">
            <Sparkles className="w-4 h-4 fill-lime-600/30" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col truncate">
              <span className="font-bold text-sm tracking-tight text-ink">Skill Issue</span>
              <span className="text-[10px] text-ink-subtle -mt-0.5 truncate">Now we have data.</span>
            </div>
          )}
        </Link>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-md text-ink-muted hover:text-ink hover:bg-surface-subtle transition-colors flex-shrink-0"
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
          className={`w-full flex items-center justify-between py-2 rounded-lg bg-surface-subtle hover:bg-surface-muted/60 text-ink-muted border border-surface-border text-xs transition-colors ${
            isCollapsed ? 'px-2 justify-center' : 'px-3'
          }`}
          title="Search actions (⌘K)"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Command className="w-3.5 h-3.5 flex-shrink-0 text-ink-muted" />
            {!isCollapsed && <span className="font-medium truncate">Search actions...</span>}
          </div>
          {!isCollapsed && (
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-white border border-surface-border rounded text-ink-muted">
              ⌘K
            </kbd>
          )}
        </button>
      </div>

      {/* Main Navigation Items */}
      <nav className="flex-1 px-2.5 space-y-1 overflow-y-auto">
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
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                isActive
                  ? 'bg-lime-50 text-lime-900 border border-lime-300 font-semibold'
                  : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={`w-4 h-4 flex-shrink-0 ${
                    isActive ? 'text-lime-700' : 'text-ink-muted group-hover:text-ink'
                  }`}
                />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </div>

              {!isCollapsed && (
                <span className="text-[10px] font-mono text-ink-subtle opacity-0 group-hover:opacity-100 transition-opacity">
                  {item.shortcut}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Bottom Footer Section */}
      <div className="p-2.5 border-t border-surface-border space-y-1.5 bg-surface-warm/30">
        {/* Model Provider Status Pill */}
        <Link
          to="/settings/provider"
          className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-surface-subtle text-xs transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="Configure AI Provider & Spending Budget"
        >
          <div
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              providerConfig?.is_valid ? 'bg-lime-500' : 'bg-amber-400'
            }`}
          />
          {!isCollapsed && (
            <div className="flex flex-col truncate">
              <span className="text-[11px] font-semibold text-ink truncate">
                {providerConfig?.is_valid ? 'Bedrock BYOC' : 'Setup Required'}
              </span>
              <span className="text-[10px] text-ink-muted truncate">
                {providerConfig?.is_valid
                  ? providerConfig.aws_region
                  : 'Configure IAM Key'}
              </span>
            </div>
          )}
        </Link>

        {/* AWS Setup Docs */}
        <Link
          to="/docs/aws-bedrock-setup"
          className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-subtle text-xs transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="AWS Bedrock Setup Guide"
        >
          <BookOpen className="w-4 h-4 flex-shrink-0 text-ink-muted" />
          {!isCollapsed && <span className="truncate">Bedrock Guide</span>}
        </Link>

        {/* Settings */}
        <Link
          to="/settings/provider"
          className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-surface-subtle text-xs transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
          title="Settings (⌘,)"
        >
          <Settings className="w-4 h-4 flex-shrink-0 text-ink-muted" />
          {!isCollapsed && <span className="truncate">Settings</span>}
        </Link>

        {/* User Account / Sign Out */}
        <div className="pt-1 border-t border-surface-border/60">
          <button
            onClick={logout}
            className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50 text-xs transition-colors ${
              isCollapsed ? 'justify-center' : ''
            }`}
            title="Sign Out"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && <span className="truncate">Sign Out</span>}
          </button>
        </div>
      </div>
    </aside>
  );
};
