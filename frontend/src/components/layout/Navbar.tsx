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
              <div className="w-8 h-8 rounded-lg bg-lime-500/15 border border-lime-500/30 flex items-center justify-center text-lime-700 group-hover:scale-105 transition-transform">
                <Sparkles className="w-4 h-4 fill-lime-600/30" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-base tracking-tight text-ink">Skill Issue</span>
                <span className="text-[10px] text-ink-subtle hidden sm:inline -mt-0.5">
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
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        isActive
                          ? 'bg-lime-50 text-lime-800 border border-lime-200'
                          : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
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
                    variant={providerConfig?.provider_name === 'bedrock' ? 'lime' : 'zinc'}
                    className="cursor-pointer hover:opacity-85 transition-opacity"
                  >
                    <Cpu className="w-3 h-3 mr-1" />
                    {providerConfig?.provider_name === 'bedrock'
                      ? providerConfig.preferred_model.includes('qwen3')
                        ? 'Bedrock (Qwen3)'
                        : 'Bedrock BYOC'
                      : 'Mock Provider (Dev)'}
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
