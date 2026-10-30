import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth';
import { api } from '../../lib/api';
import { ProviderConfig } from '../../lib/types';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import {
  Code,
  Compass,
  Cpu,
  Flame,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);

  useEffect(() => {
    if (user) {
      api.get<ProviderConfig>('/providers/config')
        .then(setProviderConfig)
        .catch(() => {});
    }
  }, [user, location.pathname]);

  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Practice', path: '/interviews/new', icon: Compass },
    { label: 'Planly', path: '/planly', icon: Flame },
    { label: 'Progress', path: '/progress', icon: TrendingUp },
    { label: 'Coding', path: '/coding', icon: Code },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-md border-b border-surface-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand Tagline */}
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200/80 flex items-center justify-center text-indigo-600 shadow-xs group-hover:scale-105 transition-all">
                <Sparkles className="w-5 h-5 fill-indigo-500/20 text-indigo-600" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-ink">Skill Issue</span>
                <span className="text-xs text-ink-subtle hidden sm:inline -mt-0.5">
                  Now we have data.
                </span>
              </div>
            </Link>

            {/* Main Nav Links */}
            {user && (
              <nav className="hidden md:flex items-center gap-1 ml-4">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isActive
                          ? 'bg-indigo-50 text-indigo-700 font-semibold border border-indigo-200/70 shadow-xs'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            )}
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3">
            {user ? (
              <>
                {/* Active Provider Indicator */}
                <Link to="/settings/provider" title="Configure AI Provider">
                  <Badge
                    variant={providerConfig?.is_valid ? 'emerald' : 'zinc'}
                    className="cursor-pointer hover:opacity-85 transition-opacity"
                  >
                    <Cpu className="w-3 h-3 mr-1" />
                    {providerConfig?.is_valid
                      ? 'Bedrock BYOC'
                      : 'Bedrock Setup Required'}
                  </Badge>
                </Link>

                <Link to="/docs/aws-bedrock-setup" className="text-xs text-ink-subtle hover:text-ink hidden lg:inline">
                  AWS Setup Guide
                </Link>

                <Link
                  to="/settings/provider"
                  className="p-1.5 text-ink-muted hover:text-ink rounded-md hover:bg-surface-subtle transition-colors"
                  title="Settings"
                >
                  <Settings className="w-4 h-4" />
                </Link>

                <div className="h-4 w-px bg-surface-border hidden sm:block" />

                <span className="text-xs text-ink-muted font-medium hidden sm:inline truncate max-w-[150px]">
                  {user.email}
                </span>

                <Button variant="ghost" size="sm" onClick={logout} title="Sign Out">
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </Button>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button variant="ghost" size="sm">Sign In</Button>
                </Link>
                <Link to="/register">
                  <Button variant="primary" size="sm">Get Started</Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
