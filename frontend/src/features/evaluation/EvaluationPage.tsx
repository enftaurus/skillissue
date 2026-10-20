import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
  Cell,
} from 'recharts';
import { api } from '../../lib/api';
import { Evaluation, EvaluationComparison, Plan } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Flame,
  HelpCircle,
  Quote,
  ShieldCheck,
  BookOpen,
  Sparkles,
} from 'lucide-react';

export const EvaluationPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [isGeneratingEval, setIsGeneratingEval] = useState(false);
  const [error, setError] = useState('');
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({ 0: true });
  const [activeChartTab, setActiveChartTab] = useState<'diverging' | 'grouped'>('diverging');

  const loadEvaluationData = async () => {
    if (!id) return;
    try {
      const evalData = await api.get<Evaluation>(`/evaluations/${id}`);
      setEvaluation(evalData);
      try {
        const compData = await api.get<EvaluationComparison>(`/evaluations/${id}/comparison`);
        setComparison(compData);
      } catch {
        // comparison can be empty if self-eval wasn't submitted
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load evaluation findings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluationData();
  }, [id]);

  const toggleQuestion = (index: number) => {
    setExpandedQuestions((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const handleGenerateEvaluation = async () => {
    if (!id) return;
    setIsGeneratingEval(true);
    setError('');
    try {
      const evalData = await api.post<Evaluation>(`/evaluations/${id}/generate`);
      setEvaluation(evalData);
      try {
        const compData = await api.get<EvaluationComparison>(`/evaluations/${id}/comparison`);
        setComparison(compData);
      } catch {
        // Optional comparison
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate evaluation report.');
    } finally {
      setIsGeneratingEval(false);
    }
  };

  const handleGeneratePlan = async () => {
    if (!evaluation) return;
    setIsGeneratingPlan(true);
    try {
      await api.post<Plan>(`/plans/generate/${evaluation.id}`);
      navigate(`/planly`);
    } catch (err: any) {
      setError(err.message || 'Failed to generate Planly roadmap.');
      setIsGeneratingPlan(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full" />
        <p className="mt-3 text-sm text-ink-muted">Synthesizing evidence-based evaluation...</p>
      </div>
    );
  }

  if (error || !evaluation) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 text-center space-y-4">
        <p className="text-sm text-ink-muted">
          {error || 'No evaluation has been generated for this interview session yet.'}
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button
            variant="primary"
            size="sm"
            onClick={handleGenerateEvaluation}
            isLoading={isGeneratingEval}
          >
            Generate Evaluation Now
          </Button>
          <Link to="/">
            <Button variant="secondary" size="sm">Return to Dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  // Prepare chart data for Diverging / Grouped calibration
  const chartData = comparison?.dimensions.map((dim) => ({
    name: dim.dimension_name,
    selfScore: dim.self_score ?? 0,
    aiScore: dim.ai_score,
    delta: dim.delta ?? 0,
  })) || [];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="lime">Evidence-Based Coaching Evaluation</Badge>
            <span className="text-xs text-ink-subtle">Model: {evaluation.model_identifier}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink mt-1">
            Interview Performance Report
          </h1>
          <p className="text-xs text-ink-muted">
            Transcripts are verified against strict evidence rubrics. Numbers are coaching signals, not hiring decisions.
          </p>
        </div>

        <Button
          variant="primary"
          size="md"
          onClick={handleGeneratePlan}
          isLoading={isGeneratingPlan}
        >
          <Flame className="w-4 h-4 mr-1.5 fill-white" />
          Generate Planly Roadmap
        </Button>
      </div>

      {/* Overall Score & Self-Perception Calibration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 bg-surface-warm border-lime-200 flex flex-col justify-between p-6">
          <div>
            <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
              Calibrated Overall Score
            </span>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-5xl font-extrabold text-ink font-mono tracking-tight">
                {Math.round(evaluation.overall_score)}
              </span>
              <span className="text-sm text-ink-subtle font-mono">/ 100</span>
            </div>
            <div className="mt-4 inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white border border-surface-border text-xs text-ink">
              <Sparkles className="w-3.5 h-3.5 text-lime-600" />
              <span>
                {evaluation.overall_score >= 80
                  ? 'Strong Staff-level Signal'
                  : evaluation.overall_score >= 60
                  ? 'Competent with Observable Gaps'
                  : 'Critical Foundations to Fortify'}
              </span>
            </div>
          </div>
          <div className="pt-6 border-t border-surface-border/60 text-xs text-ink-subtle">
            Calculated across system trade-offs, technical depth, and communication grounding.
          </div>
        </Card>

        {/* Self-Awareness Calibration Chart */}
        <Card className="lg:col-span-2 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
                  Self-Awareness Calibration
                </h3>
                <p className="text-[11px] text-ink-muted">
                  How your self-perception compares with the evidence-based evaluation.
                </p>
              </div>
              <div className="flex items-center gap-1 bg-surface-subtle p-1 rounded-md border border-surface-border text-xs">
                <button
                  onClick={() => setActiveChartTab('diverging')}
                  className={`px-2 py-0.5 rounded font-mono text-[11px] transition-colors ${
                    activeChartTab === 'diverging'
                      ? 'bg-white font-semibold text-ink shadow-xs'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  Divergence (Delta)
                </button>
                <button
                  onClick={() => setActiveChartTab('grouped')}
                  className={`px-2 py-0.5 rounded font-mono text-[11px] transition-colors ${
                    activeChartTab === 'grouped'
                      ? 'bg-white font-semibold text-ink shadow-xs'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  Side-by-Side (1-5)
                </button>
              </div>
            </div>

            {chartData.length > 0 ? (
              <div className="h-48 w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                  {activeChartTab === 'diverging' ? (
                    <BarChart
                      data={chartData}
                      layout="vertical"
                      margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                    >
                      <XAxis
                        type="number"
                        domain={[-3, 3]}
                        ticks={[-3, -2, -1, 0, 1, 2, 3]}
                        tick={{ fontSize: 10, fill: '#71717A' }}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11, fill: '#18181B' }}
                        width={100}
                      />
                      <Tooltip
                        formatter={(val: any) => [
                          `${Number(val) > 0 ? `+${val}` : val} (Self - AI)`,
                          'Calibration Delta',
                        ]}
                        contentStyle={{
                          backgroundColor: '#FFFFFF',
                          borderColor: '#E4E4E7',
                          borderRadius: '6px',
                          fontSize: '11px',
                        }}
                      />
                      <ReferenceLine x={0} stroke="#A1A1AA" strokeWidth={1.5} />
                      <Bar dataKey="delta" radius={[2, 2, 2, 2]}>
                        {chartData.map((entry, index) => {
                          const fill =
                            entry.delta === 0
                              ? '#84CC16'
                              : entry.delta > 0
                              ? '#F59E0B' // Overconfident
                              : '#3B82F6'; // Underconfident
                          return <Cell key={`cell-${index}`} fill={fill} />;
                        })}
                      </Bar>
                    </BarChart>
                  ) : (
                    <BarChart
                      data={chartData}
                      margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                    >
                      <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#18181B' }} />
                      <YAxis domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} tick={{ fontSize: 10, fill: '#71717A' }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#FFFFFF',
                          borderColor: '#E4E4E7',
                          borderRadius: '6px',
                          fontSize: '11px',
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }} />
                      <Bar name="Candidate Self-Score" dataKey="selfScore" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                      <Bar name="AI Evaluator Score" dataKey="aiScore" fill="#84CC16" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="py-8 text-center text-xs text-ink-subtle">
                Self-evaluation comparison will populate once candidate reflection is completed.
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 text-[11px] text-ink-subtle pt-2 border-t border-surface-border">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-lime-500 inline-block" /> Calibrated (0)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> Overestimated (+Delta)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 inline-block" /> Underestimated (-Delta)
            </span>
          </div>
        </Card>
      </div>

      {/* Strengths & Weaknesses Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Strengths */}
        <Card className="border-lime-200 bg-lime-50/20 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-lime-700" />
            <h3 className="font-semibold text-sm text-lime-900">Demonstrated Strengths</h3>
          </div>
          <ul className="space-y-2 text-xs text-ink-muted">
            {evaluation.strengths.map((str, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-lime-600 font-bold">•</span>
                <span>{str}</span>
              </li>
            ))}
          </ul>
        </Card>

        {/* Priority Weaknesses */}
        <Card className="border-amber-200 bg-amber-50/20 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-700" />
            <h3 className="font-semibold text-sm text-amber-900">Priority Areas to Improve</h3>
          </div>
          <ul className="space-y-2 text-xs text-ink-muted">
            {evaluation.weaknesses.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-amber-600 font-bold">•</span>
                <span>{w}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Missing Concepts */}
      {evaluation.missing_concepts.length > 0 && (
        <Card className="p-5 space-y-3">
          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
            Missing Architectural Concepts & Topics
          </span>
          <div className="flex flex-wrap gap-2">
            {evaluation.missing_concepts.map((concept, i) => (
              <Badge key={i} variant="zinc">
                {concept}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Per-Question Verbatim Feedback Accordion */}
      {evaluation.question_feedback && evaluation.question_feedback.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-ink">Per-Question Verbatim Feedback</h3>
              <Badge variant="lime" className="gap-1 font-mono text-[10px]">
                <ShieldCheck className="w-3 h-3 text-lime-700" />
                Transcript-Grounded
              </Badge>
            </div>
            <span className="text-xs text-ink-subtle">
              Every critique is anchored to exact statements made during the interview
            </span>
          </div>

          <div className="space-y-3">
            {evaluation.question_feedback.map((qf, idx) => {
              const isExpanded = !!expandedQuestions[idx];
              return (
                <div
                  key={idx}
                  className="rounded-lg border border-surface-border bg-white overflow-hidden shadow-xs transition-all"
                >
                  {/* Accordion Header */}
                  <button
                    onClick={() => toggleQuestion(idx)}
                    className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-surface-warm/50 transition-colors"
                  >
                    <div className="flex items-start gap-3 pr-4">
                      <span className="shrink-0 w-6 h-6 rounded-full bg-surface-subtle border border-surface-border text-xs font-mono font-bold flex items-center justify-center text-ink mt-0.5">
                        {qf.question_index || idx + 1}
                      </span>
                      <div>
                        <h4 className="font-semibold text-xs sm:text-sm text-ink leading-snug">
                          {qf.interviewer_question}
                        </h4>
                        <p className="text-[11px] text-ink-muted line-clamp-1 mt-0.5">
                          Candidate: &ldquo;{qf.candidate_answer}&rdquo;
                        </p>
                      </div>
                    </div>
                    <div className="shrink-0 text-ink-subtle">
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </button>

                  {/* Accordion Body */}
                  {isExpanded && (
                    <div className="px-5 pb-5 pt-2 border-t border-surface-border/60 space-y-4 bg-surface-subtle/30 text-xs">
                      {/* Candidate Quote Highlight */}
                      {qf.verbatim_quote && (
                        <div className="p-3 bg-white rounded-md border border-lime-200/80 space-y-1">
                          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-lime-800">
                            <Quote className="w-3 h-3 text-lime-700" />
                            <span>Verbatim Candidate Quote Highlighted</span>
                          </div>
                          <p className="italic text-ink font-mono text-[11px] pl-4 border-l-2 border-lime-500">
                            &ldquo;{qf.verbatim_quote}&rdquo;
                          </p>
                        </div>
                      )}

                      {/* Gilfoyle Critique */}
                      <div className="p-3.5 bg-amber-50/50 rounded-md border border-amber-200/70 space-y-1">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-900">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                          <span>Evaluation Critique</span>
                        </div>
                        <p className="text-ink leading-relaxed pl-5">
                          {qf.critique}
                        </p>
                      </div>

                      {/* Staff-Level Response Guide */}
                      <div className="p-3.5 bg-lime-50/40 rounded-md border border-lime-200/70 space-y-1">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-lime-900">
                          <Sparkles className="w-3.5 h-3.5 text-lime-700" />
                          <span>Staff-Level Engineering Model Answer</span>
                        </div>
                        <p className="text-ink leading-relaxed pl-5">
                          {qf.strong_answer_guide}
                        </p>
                      </div>

                      {/* Targeted Resource */}
                      {qf.targeted_resource && (
                        <div className="flex items-center gap-2 text-ink-subtle pt-1 text-[11px]">
                          <BookOpen className="w-3.5 h-3.5 text-lime-700" />
                          <span>Recommended Deep Dive:</span>
                          <span className="font-medium text-ink underline">{qf.targeted_resource}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Rubric Dimensions with Direct Evidence Quotes */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-ink">Rubric Dimensions & Transcript Evidence</h3>
        <div className="space-y-3">
          {comparison?.dimensions.map((dim) => (
            <Card key={dim.dimension_id} className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-sm text-ink">{dim.dimension_name}</h4>
                  <p className="text-xs text-ink-subtle mt-0.5">{dim.explanation}</p>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <span className="text-lg font-bold text-lime-700 font-mono">
                    {dim.ai_score}/5
                  </span>
                </div>
              </div>

              {dim.evidence_quote && (
                <div className="p-3 bg-surface-warm rounded-md border border-surface-border text-xs text-ink-muted flex items-start gap-2 italic">
                  <Quote className="w-3.5 h-3.5 text-lime-700 shrink-0 mt-0.5 not-italic" />
                  <span>&ldquo;{dim.evidence_quote}&rdquo;</span>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Uncertainty Disclosures */}
      {evaluation.uncertainty_notes && evaluation.uncertainty_notes.length > 0 && (
        <div className="p-4 rounded-lg bg-surface-subtle border border-surface-border text-xs text-ink-subtle flex items-start gap-2">
          <HelpCircle className="w-4 h-4 shrink-0 mt-0.5 text-ink-muted" />
          <div>
            <span className="font-semibold text-ink">Evaluator Uncertainty Disclosure: </span>
            {evaluation.uncertainty_notes.join(' · ')}
          </div>
        </div>
      )}

      {/* Bottom Action */}
      <div className="pt-4 flex justify-between items-center border-t border-surface-border">
        <Link to="/interviews/new">
          <Button variant="secondary" size="md">
            Start Another Practice Round
          </Button>
        </Link>

        <Button
          variant="primary"
          size="md"
          onClick={handleGeneratePlan}
          isLoading={isGeneratingPlan}
        >
          <Flame className="w-4 h-4 mr-1.5 fill-white" />
          Build Planly Improvement Schedule
        </Button>
      </div>
    </div>
  );
};
