import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { FunnelTelemetry } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import {
  Activity,
  Cpu,
  Mic,
  Volume2,
  Sparkles,
} from 'lucide-react';

export const AdminFunnelPage: React.FC = () => {
  const [telemetry, setTelemetry] = useState<FunnelTelemetry | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<FunnelTelemetry>('/analytics/funnel')
      .then(setTelemetry)
      .catch((err) => console.error('Failed to load funnel telemetry', err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-ink-muted">Loading funnel telemetry...</p>
      </div>
    );
  }

  if (!telemetry) {
    return (
      <div className="py-20 text-center text-xs text-ink-muted">
        Funnel telemetry unavailable.
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="bg-white border border-surface-border rounded-xl p-6 sm:p-8 shadow-card space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-500/10 border border-lime-500/20 text-lime-800 text-xs font-semibold">
          <Activity className="w-3.5 h-3.5 text-lime-700" />
          Platform Funnel & Provider Telemetry
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">
          Student Activation & Conversion Funnel
        </h1>
        <p className="text-xs sm:text-sm text-ink-muted leading-relaxed max-w-3xl">
          Track student progression across the core preparation loop: Registration $\to$ 1st Mock Interview $\to$
          AI Evaluation $\to$ Date-Driven Planly $\to$ Weakness Retest Delta.
        </p>

        <div className="mt-4 p-4 rounded-xl bg-lime-50/50 border border-lime-500/20 text-xs font-medium text-lime-950 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-lime-700 flex-shrink-0" />
          <span>{telemetry.conversion_headline}</span>
        </div>
      </div>

      {/* Funnel Stage Visualization */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-ink">Activation Stage Drop-off Analysis</h2>
        <div className="space-y-3">
          {telemetry.steps.map((step, idx) => {
            const isFirst = idx === 0;

            return (
              <Card key={idx} className="p-5 border border-surface-border">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1 max-w-xl">
                    <div className="flex items-center gap-2.5">
                      <span className="w-6 h-6 rounded-full bg-surface-subtle font-mono text-xs font-bold flex items-center justify-center text-ink-muted">
                        {idx + 1}
                      </span>
                      <h3 className="font-bold text-sm text-ink">{step.step_name}</h3>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {step.count} Users
                      </Badge>
                    </div>
                    <p className="text-xs text-ink-muted leading-relaxed pl-8">
                      {step.description}
                    </p>
                  </div>

                  {/* Percentage stats */}
                  <div className="flex items-center gap-6 text-xs font-mono pl-8 sm:pl-0">
                    <div>
                      <span className="text-ink-subtle uppercase tracking-wider text-[10px]">Conversion</span>
                      <p className="text-base font-bold text-emerald-600 mt-0.5">{step.conversion_rate}%</p>
                    </div>
                    {!isFirst && (
                      <div>
                        <span className="text-ink-subtle uppercase tracking-wider text-[10px]">Drop-off</span>
                        <p className="text-base font-bold text-red-600 mt-0.5">{step.drop_off_rate}%</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress Visual */}
                <div className="mt-3 w-full h-1.5 bg-surface-subtle rounded-full overflow-hidden border border-surface-border">
                  <div
                    className="h-full bg-lime-500 rounded-full transition-all duration-300"
                    style={{ width: `${step.conversion_rate}%` }}
                  />
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Provider Reliability & Latency Telemetry */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-ink">Inference & Audio Engine Observability</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="p-5 space-y-3 border border-surface-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-lime-600" />
                <h3 className="font-bold text-xs text-ink">Edge Neural TTS</h3>
              </div>
              <Badge variant="success" className="text-[10px] uppercase font-mono">
                Active
              </Badge>
            </div>
            <p className="text-2xl font-bold font-mono text-ink">
              {telemetry.provider_reliability?.edge_neural_tts?.latency_ms || 320}
              <span className="text-xs font-normal text-ink-muted ml-1">ms avg</span>
            </p>
            <p className="text-[11px] text-ink-subtle font-mono">
              Direct Open Protocol • Zero Cloud Key Needed
            </p>
          </Card>

          <Card className="p-5 space-y-3 border border-surface-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-indigo-600" />
                <h3 className="font-bold text-xs text-ink">Faster-Whisper STT</h3>
              </div>
              <Badge variant="success" className="text-[10px] uppercase font-mono">
                Local CPU
              </Badge>
            </div>
            <p className="text-2xl font-bold font-mono text-ink">
              {telemetry.provider_reliability?.faster_whisper_stt?.latency_ms || 440}
              <span className="text-xs font-normal text-ink-muted ml-1">ms avg</span>
            </p>
            <p className="text-[11px] text-ink-subtle font-mono">
              Local tiny.en in-memory thread pool
            </p>
          </Card>

          <Card className="p-5 space-y-3 border border-surface-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-amber-600" />
                <h3 className="font-bold text-xs text-ink">Inference Engine</h3>
              </div>
              <Badge variant="outline" className="text-[10px] uppercase font-mono">
                BYOC Dual
              </Badge>
            </div>
            <p className="text-sm font-bold font-mono text-ink pt-2">
              AWS Bedrock + Azure OpenAI
            </p>
            <p className="text-[11px] text-ink-subtle font-mono">
              Mock fallback enabled for offline development
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
};
