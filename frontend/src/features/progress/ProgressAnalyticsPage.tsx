import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../../lib/api';
import { AnalyticsDashboard, UserSkill } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Flame,
  Layers,
  Minus,
  PlayCircle,
  Quote,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react';

export const ProgressAnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [skills, setSkills] = useState<UserSkill[]>([]);
  const [expandedSkillEvidence, setExpandedSkillEvidence] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true);
      setError(null);
      try {
        const [res, skillsRes] = await Promise.all([
          api.get<AnalyticsDashboard>('/analytics/dashboard'),
          api.get<UserSkill[]>('/analytics/skills').catch(() => [] as UserSkill[]),
        ]);
        setData(res);
        setSkills(skillsRes);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('Failed to load progress analytics.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const toggleEvidence = (skillId: string) => {
    setExpandedSkillEvidence((prev) => ({
      ...prev,
      [skillId]: !prev[skillId],
    }));
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-slate-500">Crunching your interview data & progress metrics...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-sm text-rose-600 mb-4">{error || 'Unable to retrieve analytics.'}</p>
        <Link to="/interviews/new">
          <Button variant="primary">Start Your First Interview</Button>
        </Link>
      </div>
    );
  }

  // Topics sorted by score descending
  const sortedSkills = [...skills].sort((a, b) => b.score - a.score);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200/80 font-medium">
              Progress Analytics
            </span>
            <span className="text-xs text-ink-subtle">
              Evidence-based trajectory
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">
            Have I Actually Improved?
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Persistent skill graph updated via Exponential Moving Average (α=0.3) with transcript evidence quotes.
          </p>
        </div>

        <Link to="/interviews/new">
          <Button variant="primary" size="sm" className="gap-1.5">
            <PlayCircle className="w-4 h-4" />
            Launch Reassessment
          </Button>
        </Link>
      </div>

      {/* Top 4 Metric KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 bg-white border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
              Interviews Completed
            </span>
            <BarChart3 className="w-4 h-4 text-ink-muted" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-ink">
              {data.completed_interviews}
            </span>
            <span className="text-xs text-ink-muted font-mono">/ {data.total_interviews} total</span>
          </div>
          <p className="text-xs text-ink-subtle mt-1">Full sessions evaluated</p>
        </Card>

        <Card className="p-5 bg-white border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
              Avg. Rubric Score
            </span>
            <Sparkles className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-indigo-600">
              {data.average_overall_score}
            </span>
            <span className="text-xs text-ink-muted font-mono">/ 100</span>
          </div>
          <p className="text-xs text-ink-subtle mt-1">Across all completed interviews</p>
        </Card>

        <Card className="p-5 bg-white border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
              Planly Tasks Finished
            </span>
            <Flame className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-ink">
              {data.plan_tasks_completed}
            </span>
            <span className="text-xs text-ink-muted font-mono">/ {data.plan_tasks_total}</span>
          </div>
          <p className="text-xs text-ink-subtle mt-1">{data.planly_completion_rate}% completion rate</p>
        </Card>

        <Card className="p-5 bg-white border border-surface-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
              Reassessments Run
            </span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-ink">
              {data.reassessments.length}
            </span>
            <span className="text-xs text-ink-muted">verified cycles</span>
          </div>
          <p className="text-xs text-ink-subtle mt-1">Measured on identical rubrics</p>
        </Card>
      </div>

      {/* Persistent Skill Map (ADR 0012) */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold tracking-tight text-ink flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              Persistent Skill Map
            </h2>
            <p className="text-xs text-ink-subtle">
              Calibrated competency ratings that persist across mock interviews and track mastery over time.
            </p>
          </div>
        </div>

        {sortedSkills.length === 0 ? (
          <Card className="p-8 text-center bg-white border border-surface-border">
            <p className="text-sm text-ink-muted mb-1">No skill data indexed yet.</p>
            <p className="text-xs text-ink-subtle max-w-md mx-auto">
              Complete your first mock interview to seed your persistent skill graph with evidence-based scores.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sortedSkills.map((skill) => {
              const isEvidenceOpen = !!expandedSkillEvidence[skill.id];
              const confPercent = Math.round(skill.confidence * 100);
              const scoreColor =
                skill.score >= 75
                  ? 'bg-emerald-500'
                  : skill.score >= 50
                  ? 'bg-indigo-500'
                  : 'bg-rose-500';

              return (
                <Card
                  key={skill.id}
                  className="p-5 bg-white border border-surface-border hover:border-zinc-300 transition-all flex flex-col justify-between space-y-3"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-1.5">
                          <Badge variant="brand" size="sm" className="font-mono text-xs">
                            Last updated {new Date(skill.last_seen).toLocaleDateString()}
                          </Badge>
                          <span className="text-xs text-ink-subtle font-mono">
                            {skill.evidence_refs?.length || 1} signal{(skill.evidence_refs?.length || 1) !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <h4 className="font-bold text-sm text-ink mt-1">
                          {skill.topic}
                        </h4>
                      </div>

                      <div className="text-right">
                        <span className="font-mono font-extrabold text-lg text-ink">
                          {Math.round(skill.score)}
                        </span>
                        <span className="text-xs text-ink-subtle font-mono">/100</span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-2 bg-surface-subtle rounded-full overflow-hidden border border-surface-border mt-3">
                      <div
                        className={`h-full ${scoreColor} rounded-full transition-all duration-500`}
                        style={{ width: `${Math.min(100, Math.max(5, skill.score))}%` }}
                      />
                    </div>

                    {/* Confidence Indicator */}
                    <div className="flex items-center justify-between text-[11px] text-ink-subtle mt-2">
                      <span className="flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Confidence: {confPercent}%</span>
                      </span>
                      <span>
                        {skill.confidence >= 0.7
                          ? 'High Calibration'
                          : skill.confidence >= 0.4
                          ? 'Calibrating'
                          : 'Early Signal'}
                      </span>
                    </div>
                  </div>

                  {/* Evidence Drawer Toggle */}
                  {skill.evidence_refs && skill.evidence_refs.length > 0 && (
                    <div className="pt-2 border-t border-surface-border/60">
                      <button
                        onClick={() => toggleEvidence(skill.id)}
                        className="w-full flex items-center justify-between text-xs text-ink-muted hover:text-ink font-medium"
                      >
                        <span className="flex items-center gap-1.5">
                          <Quote className="w-3 h-3 text-indigo-600" />
                          <span>Evaluation Evidence History ({skill.evidence_refs.length})</span>
                        </span>
                        {isEvidenceOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isEvidenceOpen && (
                        <div className="mt-2.5 space-y-1.5 pt-1">
                          {skill.evidence_refs.map((ref: any, qIdx: number) => (
                            <div
                              key={qIdx}
                              className="p-2 rounded bg-surface-warm border border-surface-border text-xs text-ink flex items-center justify-between"
                            >
                              <span className="capitalize text-ink-muted font-mono">{ref.type || 'evaluation'} signal</span>
                              <span className="font-mono font-bold text-indigo-700">
                                {ref.score !== undefined ? `${Math.round(ref.score)}/100` : 'Recorded'}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Reassessment Before-and-After Comparisons */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold tracking-tight text-ink flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-600" />
            Verified Reassessment Cycles
          </h2>
          <span className="text-xs text-ink-subtle">
            Only interviews with matching rubric categories qualify as reassessments
          </span>
        </div>

        {data.reassessments.length === 0 ? (
          <Card className="p-8 text-center bg-white border border-surface-border">
            <p className="text-sm text-ink-muted mb-2">No reassessments completed yet.</p>
            <p className="text-xs text-ink-subtle max-w-md mx-auto mb-4">
              Complete an interview, finish your Planly action items, and then take another interview
              in the same category to measure verified delta on identical rubrics.
            </p>
            <Link to="/interviews/new">
              <Button variant="secondary" size="sm">Start Practice</Button>
            </Link>
          </Card>
        ) : (
          <div className="space-y-4">
            {data.reassessments.map((r, idx) => {
              const isPositive = r.score_delta > 0;
              const isNeutral = r.score_delta === 0;

              return (
                <Card key={idx} className="p-6 bg-white border border-surface-border hover:border-zinc-300 transition-all">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    {/* Baseline vs Reassessment Info */}
                    <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Baseline */}
                      <div className="p-3.5 rounded-lg bg-surface-subtle border border-surface-border space-y-1">
                        <span className="text-[10px] font-mono uppercase text-ink-subtle tracking-wider block">
                           Baseline Interview
                        </span>
                        <Link
                          to={`/evaluations/${r.baseline_interview_id}`}
                          className="font-semibold text-sm text-ink hover:text-indigo-600 hover:underline block truncate"
                        >
                          {r.baseline_title}
                        </Link>
                        <div className="flex items-center justify-between text-xs text-ink-muted pt-1">
                          <span>{new Date(r.baseline_date).toLocaleDateString()}</span>
                          <span className="font-mono font-bold text-ink">{r.baseline_score}/100</span>
                        </div>
                      </div>

                      {/* Reassessment */}
                      <div className="p-3.5 rounded-lg bg-indigo-50/40 border border-indigo-200/80 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-indigo-800 tracking-wider block">
                          Reassessment Interview
                        </span>
                        <Link
                          to={`/evaluations/${r.reassessment_interview_id}`}
                          className="font-semibold text-sm text-ink hover:text-indigo-600 hover:underline block truncate"
                        >
                          {r.reassessment_title}
                        </Link>
                        <div className="flex items-center justify-between text-xs text-ink-muted pt-1">
                          <span>{new Date(r.reassessment_date).toLocaleDateString()}</span>
                          <span className="font-mono font-bold text-indigo-800">{r.reassessment_score}/100</span>
                        </div>
                      </div>
                    </div>

                    {/* Score Delta Badge */}
                    <div className="flex md:flex-col items-center md:items-end justify-between md:justify-center border-t md:border-t-0 md:border-l border-surface-border pt-4 md:pt-0 md:pl-6 min-w-[130px]">
                      <span className="text-xs text-ink-subtle uppercase tracking-wider font-semibold">
                        Score Delta
                      </span>
                      <div
                        className={`text-2xl font-bold font-mono mt-1 flex items-center gap-1 ${
                          isPositive
                            ? 'text-emerald-700'
                            : isNeutral
                            ? 'text-ink-muted'
                            : 'text-rose-600'
                        }`}
                      >
                        {isPositive ? (
                          <ArrowUpRight className="w-5 h-5 text-emerald-600" />
                        ) : isNeutral ? (
                          <Minus className="w-5 h-5" />
                        ) : (
                          <ArrowDownRight className="w-5 h-5 text-rose-600" />
                        )}
                        {isPositive ? `+${r.score_delta}` : `${r.score_delta}`} pts
                      </div>
                    </div>
                  </div>

                  {/* Dimensions Delta Tags */}
                  <div className="mt-4 pt-4 border-t border-surface-border flex flex-wrap items-center gap-4 text-xs">
                    {r.improved_dimensions.length > 0 && (
                      <div className="flex items-center gap-1.5 text-emerald-800">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="font-medium">Improved:</span>{' '}
                        <span>{r.improved_dimensions.join(', ')}</span>
                      </div>
                    )}
                    {r.stable_dimensions.length > 0 && (
                      <div className="flex items-center gap-1.5 text-ink-muted">
                        <Minus className="w-3.5 h-3.5" />
                        <span className="font-medium">Stable:</span>{' '}
                        <span>{r.stable_dimensions.join(', ')}</span>
                      </div>
                    )}
                    {r.declined_dimensions.length > 0 && (
                      <div className="flex items-center gap-1.5 text-rose-700">
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                        <span className="font-medium">Declined:</span>{' '}
                        <span>{r.declined_dimensions.join(', ')}</span>
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Dimension Trends & Recurring Strengths/Weaknesses */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Dimension Trends (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-bold tracking-tight text-ink flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-600" />
            Rubric Dimension Averages
          </h2>

          <Card className="p-6 bg-white border border-surface-border space-y-5">
            {data.dimension_trends.length === 0 ? (
              <p className="text-sm text-ink-muted">
                Dimension trends will appear as you complete scored interviews.
              </p>
            ) : (
              data.dimension_trends.map((dim) => {
                const percent = Math.min(100, Math.round(dim.average_score * 20)); // out of 5 -> percent
                return (
                  <div key={dim.dimension_id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-ink">{dim.dimension_name}</span>
                      <div className="flex items-center gap-2 font-mono">
                        <span className="text-ink font-bold">{dim.latest_score.toFixed(1)}/5.0</span>
                        <span className="text-ink-subtle">
                          (avg {dim.average_score.toFixed(1)})
                        </span>
                      </div>
                    </div>
                    <div className="w-full h-2.5 bg-surface-subtle rounded-full overflow-hidden border border-surface-border">
                      <div
                        className="h-full bg-indigo-600 rounded-full transition-all duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </Card>

          {/* Recent Score Timeline */}
          {data.score_history.length > 0 && (
            <Card className="p-6 bg-white border border-surface-border space-y-4">
              <h3 className="text-sm font-semibold text-ink uppercase tracking-wider text-xs">
                Score Timeline History
              </h3>
              <div className="space-y-2">
                {data.score_history.slice(0, 5).map((s) => (
                  <div
                    key={s.interview_id}
                    className="flex items-center justify-between p-3 rounded-lg bg-surface-subtle border border-surface-border text-xs"
                  >
                    <div>
                      <Link
                        to={`/evaluations/${s.interview_id}`}
                        className="font-semibold text-ink hover:text-indigo-600"
                      >
                        {s.title}
                      </Link>
                      <div className="text-[11px] text-ink-muted mt-0.5">
                        {s.category} • {new Date(s.completed_at).toLocaleDateString()}
                      </div>
                    </div>
                    <span className="font-mono font-bold text-sm text-indigo-800 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-200/80">
                      {s.overall_score}/100
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right col: Recurring Strengths & Recurring Weaknesses */}
        <div className="space-y-6">
          <Card className="p-6 bg-white border border-surface-border space-y-3">
            <h3 className="text-sm font-semibold text-emerald-800 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Verified Strengths
            </h3>
            <p className="text-xs text-ink-subtle">
              Consistently demonstrated across multiple interview sessions:
            </p>
            {data.recurring_strengths.length === 0 ? (
              <p className="text-xs text-ink-muted italic">
                None identified yet. Complete more sessions to build patterns.
              </p>
            ) : (
              <ul className="space-y-2">
                {data.recurring_strengths.map((str, i) => (
                  <li
                    key={i}
                    className="text-xs text-ink bg-emerald-50/60 border border-emerald-200/80 p-2.5 rounded-md leading-relaxed"
                  >
                    {str}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="p-6 bg-white border border-surface-border space-y-3">
            <h3 className="text-sm font-semibold text-rose-800 flex items-center gap-2">
              <XCircle className="w-4 h-4 text-rose-600" />
              Recurring Blind Spots
            </h3>
            <p className="text-xs text-ink-subtle">
              Patterns that interviewers repeatedly flag for follow-up or correction:
            </p>
            {data.recurring_weaknesses.length === 0 ? (
              <p className="text-xs text-ink-muted italic">
                None identified yet. Complete more sessions to build patterns.
              </p>
            ) : (
              <ul className="space-y-2">
                {data.recurring_weaknesses.map((weak, i) => (
                  <li
                    key={i}
                    className="text-xs text-ink bg-rose-50/60 border border-rose-200/80 p-2.5 rounded-md leading-relaxed"
                  >
                    {weak}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
