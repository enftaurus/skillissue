import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { ProviderConfig } from '../../lib/types';
import { Zap, ChevronRight, X } from 'lucide-react';

export const CreditsUsageBadge: React.FC = () => {
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchUsage = () => {
      api.get<ProviderConfig>('/providers/config')
        .then(setConfig)
        .catch(() => {});
    };

    fetchUsage();
    // Refresh every 30 seconds
    const interval = setInterval(fetchUsage, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (!config) return null;

  const costSpentUsd = config.estimated_cost_usd || (config.monthly_cost_cents_used ? config.monthly_cost_cents_used / 100 : 0);
  const costBudgetUsd = config.monthly_cost_cents_budget ? config.monthly_cost_cents_budget / 100 : 10.0;
  const costPercent = Math.min(100, Math.round((costSpentUsd / costBudgetUsd) * 100));

  const tokensUsed = config.total_tokens_used || config.monthly_tokens_used || 0;
  const tokenBudget = config.monthly_token_budget || 1_000_000;
  const tokenPercent = Math.min(100, Math.round((tokensUsed / tokenBudget) * 100));

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return n.toString();
  };

  const providerLabel = config.provider_name === 'azure' ? 'Azure OpenAI' : 'Amazon Bedrock';

  return (
    <div className="relative inline-block" ref={popoverRef}>
      {/* Trigger Pill */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-surface-border hover:border-lime-400 text-xs text-ink transition-all shadow-xs group"
        title="View Token & Cost Usage"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-lime-500 animate-pulse" />
        <span className="font-mono font-medium text-[11px] text-ink">
          ${costSpentUsd.toFixed(3)}
        </span>
        <span className="text-ink-subtle text-[10px]">•</span>
        <span className="font-mono text-[11px] text-ink-muted group-hover:text-ink">
          {formatTokens(tokensUsed)} tokens
        </span>
      </button>

      {/* Popover Card */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-surface-border rounded-xl shadow-lg p-4 z-50 text-xs text-ink space-y-3.5 animate-in fade-in zoom-in-95 duration-100">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
            <div className="flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-lime-600" />
              <h4 className="font-semibold text-xs text-ink">Inference & Budget Usage</h4>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-ink-subtle hover:text-ink p-0.5 rounded"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Provider pill */}
          <div className="flex items-center justify-between bg-surface-subtle p-2 rounded-lg border border-surface-border text-[11px]">
            <span className="text-ink-muted">Active BYOC Provider:</span>
            <span className="font-semibold text-ink flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-lime-500" />
              {providerLabel}
            </span>
          </div>

          {/* Cost Meter */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-ink-muted">Monthly Estimated Spend</span>
              <span className="font-mono font-semibold text-ink">
                ${costSpentUsd.toFixed(3)} <span className="text-ink-subtle font-normal">/ ${costBudgetUsd.toFixed(2)}</span>
              </span>
            </div>
            <div className="w-full bg-surface-warm rounded-full h-1.5 overflow-hidden border border-surface-border">
              <div
                className={`h-full transition-all duration-300 ${
                  costPercent > 80 ? 'bg-amber-500' : 'bg-lime-500'
                }`}
                style={{ width: `${Math.max(3, costPercent)}%` }}
              />
            </div>
          </div>

          {/* Token Meter */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-ink-muted">Tokens Consumed</span>
              <span className="font-mono font-semibold text-ink">
                {formatTokens(tokensUsed)} <span className="text-ink-subtle font-normal">/ {formatTokens(tokenBudget)}</span>
              </span>
            </div>
            <div className="w-full bg-surface-warm rounded-full h-1.5 overflow-hidden border border-surface-border">
              <div
                className="h-full bg-lime-600 transition-all duration-300"
                style={{ width: `${Math.max(3, tokenPercent)}%` }}
              />
            </div>
          </div>

          {/* Models Lineup */}
          <div className="pt-2 border-t border-surface-border text-[11px] space-y-1 text-ink-muted">
            <div className="flex justify-between">
              <span>Interviewer Model:</span>
              <span className="font-mono text-ink font-medium">{config.interviewer_model || config.preferred_model}</span>
            </div>
            <div className="flex justify-between">
              <span>Evaluation Model:</span>
              <span className="font-mono text-ink font-medium">{config.evaluation_model || 'azure.gpt-4.1'}</span>
            </div>
          </div>

          {/* Footer action */}
          <Link
            to="/settings/provider"
            onClick={() => setIsOpen(false)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-surface-warm hover:bg-surface-subtle border border-surface-border text-ink font-medium text-xs transition-colors"
          >
            <span>Adjust Monthly Spending Ceilings</span>
            <ChevronRight className="w-3.5 h-3.5 text-ink-subtle" />
          </Link>
        </div>
      )}
    </div>
  );
};
