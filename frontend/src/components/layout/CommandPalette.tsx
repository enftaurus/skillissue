import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  Code2,
  Mic,
  Calendar,
  TrendingUp,
  Settings,
  BookOpen,
  ArrowRight,
  Sparkles,
} from 'lucide-react';

interface PaletteItem {
  id: string;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  path: string;
  category: 'Navigation' | 'Practice' | 'Configuration';
  shortcut?: string;
}

const PALETTE_ITEMS: PaletteItem[] = [
  {
    id: 'nav-dashboard',
    title: 'Dashboard Overview',
    subtitle: 'View recent interviews, active Planly tasks, and readiness metric',
    icon: LayoutDashboard,
    path: '/',
    category: 'Navigation',
    shortcut: '⌘1',
  },
  {
    id: 'nav-coding',
    title: 'DSA & Coding Arena',
    subtitle: '15 standard algorithm problems with isolated Docker execution',
    icon: Code2,
    path: '/coding',
    category: 'Practice',
    shortcut: '⌘2',
  },
  {
    id: 'nav-interview',
    title: 'Start Mock Interview',
    subtitle: 'Launch domain or JD-tailored human-like technical rounds',
    icon: Mic,
    path: '/interviews/new',
    category: 'Practice',
    shortcut: '⌘3',
  },
  {
    id: 'nav-planly',
    title: 'Planly Improvement Calendar',
    subtitle: 'Adaptive daily practice roadmap generated from verified weaknesses',
    icon: Calendar,
    path: '/planly',
    category: 'Navigation',
    shortcut: '⌘4',
  },
  {
    id: 'nav-analytics',
    title: 'Skill Progress & Analytics',
    subtitle: 'Inspect persistent skill map, confidence ratings, and score deltas',
    icon: TrendingUp,
    path: '/progress',
    category: 'Navigation',
    shortcut: '⌘5',
  },
  {
    id: 'nav-settings',
    title: 'Model & BYOC Provider Settings',
    subtitle: 'Configure Amazon Bedrock credentials, spend caps, or offline mock',
    icon: Settings,
    path: '/settings/provider',
    category: 'Configuration',
    shortcut: '⌘,',
  },
  {
    id: 'nav-aws-docs',
    title: 'AWS Bedrock Setup Guide',
    subtitle: 'Step-by-step IAM permissions and model access instructions',
    icon: BookOpen,
    path: '/docs/aws-bedrock-setup',
    category: 'Configuration',
  },
];

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filteredItems = PALETTE_ITEMS.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.subtitle.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        executeItem(filteredItems[selectedIndex]);
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  const executeItem = (item: PaletteItem) => {
    navigate(item.path);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/30 backdrop-blur-sm flex items-start justify-center pt-24 px-4 sm:px-6">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className="relative w-full max-w-xl bg-white rounded-xl shadow-2xl border border-surface-border overflow-hidden transform transition-all"
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-surface-border bg-surface-warm/50">
          <Search className="w-5 h-5 text-ink-muted mr-3 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent text-sm text-ink placeholder-ink-subtle outline-none font-medium"
            placeholder="Type a command, page, or search actions..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-mono text-ink-muted bg-surface-subtle border border-surface-border rounded shadow-sm">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 divide-y divide-surface-border/50">
          {filteredItems.length === 0 ? (
            <div className="py-10 text-center text-sm text-ink-muted">
              <Sparkles className="w-6 h-6 mx-auto mb-2 text-ink-subtle" />
              <p>No matching commands found for &ldquo;{query}&rdquo;.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {filteredItems.map((item, idx) => {
                const Icon = item.icon;
                const isSelected = idx === selectedIndex;
                return (
                  <button
                    key={item.id}
                    onClick={() => executeItem(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-left transition-colors ${
                      isSelected
                        ? 'bg-lime-50 text-ink border border-lime-300'
                        : 'text-ink-muted hover:bg-surface-subtle'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={`w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0 ${
                          isSelected
                            ? 'bg-lime-200 text-lime-900'
                            : 'bg-surface-subtle text-ink-muted'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="truncate">
                        <div className="text-sm font-semibold text-ink flex items-center gap-2">
                          <span>{item.title}</span>
                          <span className="text-[10px] font-normal uppercase tracking-wider px-1.5 py-0.2 rounded bg-surface-muted/60 text-ink-muted">
                            {item.category}
                          </span>
                        </div>
                        <div className="text-xs text-ink-muted truncate">{item.subtitle}</div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                      {item.shortcut && (
                        <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-ink-muted bg-white border border-surface-border rounded">
                          {item.shortcut}
                        </kbd>
                      )}
                      <ArrowRight
                        className={`w-4 h-4 transition-transform ${
                          isSelected ? 'text-lime-700 translate-x-0.5' : 'text-transparent'
                        }`}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer Navigation Hints */}
        <div className="px-4 py-2 border-t border-surface-border bg-surface-subtle/50 flex items-center justify-between text-[11px] text-ink-muted">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-surface-border rounded font-mono text-[10px] mr-1">↑↓</kbd>
              Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-white border border-surface-border rounded font-mono text-[10px] mr-1">↵</kbd>
              Select
            </span>
          </div>
          <span>Gilfoyle-calibrated feedback</span>
        </div>
      </div>
    </div>
  );
};
