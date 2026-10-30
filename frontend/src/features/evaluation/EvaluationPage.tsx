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
import { Evaluation, EvaluationComparison, Plan, WeaknessAnalysisItem, LearningBacklogItem } from '../../lib/types';
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
  BookmarkPlus,
  Check,
  CalendarPlus,
  Copy,
  Download,
  User,
  Bot,
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
  const [activeChartTab, setActiveChartTab] = useState<'diverging' | 'grouped'>('grouped');
  const [copiedTranscript, setCopiedTranscript] = useState(false);

  // Backlog & Planly action state
  const [queueLoading, setQueueLoading] = useState<Record<string, boolean>>({});
  const [queueSuccess, setQueueSuccess] = useState<Record<string, string>>({});

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

  const handleQueueWeakness = async (weakness: WeaknessAnalysisItem) => {
    if (!evaluation) return;
    setQueueLoading((prev) => ({ ...prev, [weakness.id]: true }));
    try {
      const res = await api.post<LearningBacklogItem>('/learning-backlog/queue-weakness', {
        interview_id: evaluation.interview_id,
        weakness_id: weakness.id,
        topic: weakness.topic,
        subtopic: weakness.subtopic,
        evidence: weakness.evidence,
        gap_explanation: weakness.gap_explanation,
        learning_objective: weakness.learning_objective,
        suggested_exercise: weakness.suggested_exercise,
        priority: 'high',
        notes: `Identified in interview on ${evaluation.model_identifier}. Evidence: "${weakness.evidence}"`,
      });
      setQueueSuccess((prev) => ({
        ...prev,
        [weakness.id]: res.is_existing ? 'Updated in Backlog' : 'Queued for Later',
      }));
    } catch (err: any) {
      alert(err.message || 'Failed to queue weakness to learning backlog.');
    } finally {
      setQueueLoading((prev) => ({ ...prev, [weakness.id]: false }));
    }
  };

  const handleAddToPlanly = (weakness: WeaknessAnalysisItem) => {
    navigate(
      `/planly?action=create&topic=${encodeURIComponent(weakness.topic)}&objective=${encodeURIComponent(
        weakness.learning_objective || ''
      )}`
    );
  };

  const getFullTranscriptText = (): string => {
    if (evaluation?.stored_transcript && evaluation.stored_transcript.trim()) {
      return evaluation.stored_transcript;
    }
    if (evaluation?.transcript_turns && evaluation.transcript_turns.length > 0) {
      return evaluation.transcript_turns
        .map((t) => `[Question ${t.question_index}]\nInterviewer: ${t.interviewer_question}\nCandidate: ${t.candidate_answer}\n`)
        .join('\n');
    }
    if (evaluation?.question_feedback && evaluation.question_feedback.length > 0) {
      return evaluation.question_feedback
        .map((q, i) => `[Question ${q.question_index || i + 1}]\nInterviewer: ${q.interviewer_question}\nCandidate: ${q.candidate_answer}\n`)
        .join('\n');
    }
    return 'No transcript recorded for this session.';
  };

  const handleCopyTranscript = () => {
    const text = getFullTranscriptText();
    navigator.clipboard.writeText(text);
    setCopiedTranscript(true);
    setTimeout(() => setCopiedTranscript(false), 2500);
  };

  const handleDownloadTranscript = () => {
    const text = getFullTranscriptText();
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `interview_transcript_${id || 'session'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full" />
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
  const hasSelfEval = Boolean(
    comparison?.dimensions && comparison.dimensions.some((d) => d.self_score !== null && d.self_score !== undefined)
  );

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
            <Badge variant="indigo">Evidence-Based Coaching Evaluation</Badge>
            <span className="text-xs text-ink-subtle">Model: {evaluation.model_identifier}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-ink mt-1">
            Interview Performance Report
          </h1>
          <p className="text-xs text-ink-muted">
            Transcripts are verified against strict evidence rubrics. Numbers are coaching signals, not hiring decisions.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-subtle border border-surface-border font-mono text-xs text-ink-muted">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>
              {evaluation.tokens_used > 0
                ? `${evaluation.tokens_used.toLocaleString()} tokens`
                : 'Evaluation Inference'}
            </span>
            <span className="text-ink-subtle">•</span>
            <span className="font-semibold text-ink">
              ~${((evaluation.tokens_used || 1200) * 0.0000035).toFixed(4)} USD
            </span>
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
      </div>

      {/* Overall Score & Self-Perception Calibration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 bg-indigo-50/20 border-indigo-100 flex flex-col justify-between p-6 rounded-2xl shadow-xs">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Calibrated Overall Score
            </span>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-5xl font-extrabold text-slate-900 font-mono tracking-tight">
                {Math.round(evaluation.overall_score)}
              </span>
              <span className="text-sm text-slate-400 font-mono">/ 100</span>
            </div>
            <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200/80 text-xs font-medium text-slate-800 shadow-xs">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>
                {evaluation.overall_score >= 80
                  ? 'Strong Staff-level Signal'
                  : evaluation.overall_score >= 60
                  ? 'Competent with Observable Gaps'
                  : 'Critical Foundations to Fortify'}
              </span>
            </div>
          </div>
          <div className="pt-6 border-t border-slate-200/60 text-xs text-slate-500 leading-relaxed">
            Calculated across system trade-offs, technical depth, and communication grounding.
          </div>
        </Card>

        {/* Self-Awareness Calibration Chart & Matrix */}
        <Card className="lg:col-span-2 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
                  Self-Awareness Calibration
                </h3>
                <p className="text-xs text-ink-muted">
                  How your self-perception compares with the evidence-based evaluation.
                </p>
              </div>
              <div className="flex items-center gap-1 bg-surface-subtle p-1 rounded-md border border-surface-border text-xs">
                <button
                  onClick={() => setActiveChartTab('grouped')}
                  className={`px-2.5 py-1 rounded font-mono text-xs transition-colors ${
                    activeChartTab === 'grouped'
                      ? 'bg-white font-semibold text-ink shadow-xs'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  Side-by-Side (1-5)
                </button>
                <button
                  onClick={() => setActiveChartTab('diverging')}
                  className={`px-2.5 py-1 rounded font-mono text-xs transition-colors ${
                    activeChartTab === 'diverging'
                      ? 'bg-white font-semibold text-ink shadow-xs'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  Divergence (Delta)
                </button>
              </div>
            </div>

            {hasSelfEval && chartData.length > 0 ? (
              <>
                <div className="h-52 w-full mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    {activeChartTab === 'grouped' ? (
                      <BarChart
                        data={chartData}
                        margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
                      >
                        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#18181B' }} />
                        <YAxis domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} tick={{ fontSize: 11, fill: '#71717A' }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#FFFFFF',
                            borderColor: '#E4E4E7',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                        <Bar name="Candidate Self-Score" dataKey="selfScore" fill="#94A3B8" radius={[4, 4, 0, 0]} />
                        <Bar name="AI Evaluator Score" dataKey="aiScore" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    ) : (
                      <BarChart
                        data={chartData}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                      >
                        <XAxis
                          type="number"
                          domain={[-3, 3]}
                          ticks={[-3, -2, -1, 0, 1, 2, 3]}
                          tick={{ fontSize: 11, fill: '#71717A' }}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          tick={{ fontSize: 11, fill: '#18181B' }}
                          width={110}
                        />
                        <Tooltip
                          formatter={(val: any) => [
                            `${Number(val) > 0 ? `+${val}` : val} (Self - AI)`,
                            'Calibration Delta',
                          ]}
                          contentStyle={{
                            backgroundColor: '#FFFFFF',
                            borderColor: '#E4E4E7',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                        />
                        <ReferenceLine x={0} stroke="#A1A1AA" strokeWidth={1.5} />
                        <Bar dataKey="delta" radius={[3, 3, 3, 3]}>
                          {chartData.map((entry, index) => {
                            const fill =
                              entry.delta === 0
                                ? '#10B981' // Calibrated (Crisp Emerald)
                                : entry.delta > 0
                                ? '#F59E0B' // Overconfident (Amber)
                                : '#6366F1'; // Underconfident (Indigo)
                            return <Cell key={`cell-${index}`} fill={fill} />;
                          })}
                        </Bar>
                      </BarChart>
                    )}
                  </ResponsiveContainer>
                </div>

                {/* Dimension Calibration Matrix */}
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5 flex items-center justify-between">
                    <span>Dimension Calibration Matrix</span>
                    <span className="text-[11px] font-normal text-slate-400">Self vs Evaluator per Dimension</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {comparison?.dimensions.map((dim) => {
                      const isCalibrated = dim.delta === 0;
                      const isOver = (dim.delta || 0) > 0;
                      return (
                        <div
                          key={dim.dimension_id}
                          className={`p-2.5 rounded-xl border flex items-center justify-between gap-2 ${
                            isCalibrated
                              ? 'bg-emerald-50/40 border-emerald-200/80'
                              : isOver
                              ? 'bg-amber-50/40 border-amber-200/80'
                              : 'bg-indigo-50/40 border-indigo-200/80'
                          }`}
                        >
                          <div className="min-w-0">
                            <span className="font-semibold text-slate-900 truncate block">{dim.dimension_name}</span>
                            <span className="text-slate-500 text-[11px]">
                              Self: <strong className="text-slate-800">{dim.self_score}/5</strong> • AI: <strong className="text-slate-800">{dim.ai_score}/5</strong>
                            </span>
                          </div>
                          <Badge
                            variant={isCalibrated ? 'emerald' : isOver ? 'amber' : 'indigo'}
                            className="text-[11px] shrink-0 font-mono"
                          >
                            {isCalibrated ? '✓ Calibrated' : isOver ? `+${dim.delta} Over` : `${dim.delta} Under`}
                          </Badge>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="py-8 px-4 text-center space-y-3 bg-slate-50/70 rounded-xl border border-dashed border-slate-200 my-4">
                <HelpCircle className="w-8 h-8 text-indigo-500 mx-auto" />
                <div>
                  <h4 className="font-semibold text-sm text-slate-900">Self-Evaluation Not Recorded</h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
                    Self-review was skipped or omitted during this session. Self-awareness calibration graphs compare your self-perception against objective AI rubric evaluations.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-500 pt-3 border-t border-slate-100">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Calibrated (0)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" /> Overestimated (+Delta)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" /> Underestimated (-Delta)
            </span>
          </div>
        </Card>
      </div>

      {/* Strengths & Weaknesses Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {/* Strengths */}
        <Card className="border-emerald-200/80 bg-emerald-50/20 p-6 rounded-2xl shadow-xs space-y-3.5">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h3 className="font-semibold text-base text-emerald-950">Demonstrated Strengths</h3>
          </div>
          <ul className="space-y-2.5 text-xs sm:text-sm text-slate-700">
            {evaluation.strengths.map((str, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="text-emerald-500 font-bold">•</span>
                <span className="leading-relaxed">{str}</span>
              </li>
            ))}
          </ul>
        </Card>

        {/* Evidenced Weaknesses with Action A & Action B */}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-ink">Demonstrated Weaknesses & Actionable Diagnostics</h3>
            <Badge variant="zinc" className="font-mono text-[10px]">
              {(evaluation.weakness_analysis?.length || evaluation.weaknesses?.length || 0)} Actionable Findings
            </Badge>
          </div>
          <span className="text-xs text-ink-subtle hidden sm:inline">
            Act on findings individually: commit to a Planly schedule or queue for later revisit
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {(evaluation.weakness_analysis && evaluation.weakness_analysis.length > 0
            ? evaluation.weakness_analysis
            : (evaluation.weaknesses || []).map((w, i): WeaknessAnalysisItem => ({
                id: `w-${i}`,
                topic: w,
                subtopic: undefined,
                evidence: 'Identified during technical dialogue',
                gap_explanation: w,
                learning_objective: `Master ${w} principles and architectural trade-offs.`,
                suggested_exercise: undefined,
                confidence: 'medium' as const,
              }))
          ).map((item) => {
            const isQueued = !!queueSuccess[item.id];
            const isQInProgress = !!queueLoading[item.id];

            return (
              <Card key={item.id} className="p-5 border-amber-200/80 bg-white space-y-3.5 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-sm text-ink">{item.topic}</span>
                    {item.subtopic && (
                      <Badge variant="zinc" size="sm">
                        {item.subtopic}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={item.confidence === 'high' ? 'indigo' : 'zinc'}
                      size="sm"
                      className="capitalize text-xs"
                    >
                      {item.confidence} Evidence Confidence
                    </Badge>
                  </div>
                </div>

                {/* Evidence Quote */}
                {item.evidence && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs sm:text-sm flex items-start gap-2.5">
                    <Quote className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-slate-500 text-xs block uppercase tracking-wider mb-1">
                        Transcript Evidence:
                      </span>
                      <p className="italic text-slate-800 font-mono text-xs sm:text-sm leading-relaxed">
                        &ldquo;{item.evidence}&rdquo;
                      </p>
                    </div>
                  </div>
                )}

                {/* Gap & Learning Objective */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs sm:text-sm">
                  <div className="p-3.5 bg-amber-50/50 rounded-xl border border-amber-200/60 space-y-1.5">
                    <span className="font-semibold text-amber-900 block text-xs uppercase tracking-wider">
                      Observed Knowledge Gap:
                    </span>
                    <p className="text-slate-800 leading-relaxed">{item.gap_explanation}</p>
                  </div>

                  <div className="p-3.5 bg-indigo-50/40 rounded-xl border border-indigo-200/60 space-y-1.5">
                    <span className="font-semibold text-indigo-900 block text-xs uppercase tracking-wider">
                      Recommended Learning Objective:
                    </span>
                    <p className="text-slate-800 leading-relaxed">{item.learning_objective}</p>
                  </div>
                </div>

                {item.suggested_exercise && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs sm:text-sm text-slate-600">
                    <span className="font-semibold text-slate-900">Suggested Practice Direction: </span>
                    {item.suggested_exercise}
                  </div>
                )}

                {/* Action Buttons: Action A & Action B */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100">
                  <span className="text-xs text-slate-500">
                    {queueSuccess[item.id] ? (
                      <span className="text-indigo-700 font-medium flex items-center gap-1.5">
                        <Check className="w-4 h-4 text-emerald-600" />
                        {queueSuccess[item.id]}
                      </span>
                    ) : (
                      'Act individually: queue for later revisit or schedule in Planly'
                    )}
                  </span>

                  <div className="flex items-center gap-2.5 w-full sm:w-auto">
                    {/* Action B: Queue for later */}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleQueueWeakness(item)}
                      isLoading={isQInProgress}
                      disabled={isQueued}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-xs"
                    >
                      {isQueued ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Queued</span>
                        </>
                      ) : (
                        <>
                          <BookmarkPlus className="w-3.5 h-3.5" />
                          <span>Queue for Later</span>
                        </>
                      )}
                    </Button>

                    {/* Action A: Add to Planly */}
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={() => handleAddToPlanly(item)}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 text-xs"
                    >
                      <CalendarPlus className="w-3.5 h-3.5" />
                      <span>Add to Planly</span>
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Missing Concepts */}
      {evaluation.missing_concepts.length > 0 && (
        <Card className="p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Missing Architectural Concepts & Topics
          </span>
          <div className="flex flex-wrap gap-2">
            {evaluation.missing_concepts.map((concept, i) => (
              <Badge key={i} variant="zinc" className="text-xs">
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
              <h3 className="text-lg font-bold text-slate-900">Per-Question Verbatim Feedback</h3>
              <Badge variant="indigo" className="gap-1 font-mono text-xs">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
                Transcript-Grounded
              </Badge>
            </div>
            <span className="text-xs text-slate-500">
              Every critique is anchored to exact statements made during the interview
            </span>
          </div>

          <div className="space-y-3">
            {evaluation.question_feedback.map((qf, idx) => {
              const isExpanded = !!expandedQuestions[idx];
              const qIndex = qf.question_index || idx + 1;
              const qComp = comparison?.question_comparisons?.find((c) => c.question_index === qIndex);

              return (
                <div
                  key={idx}
                  className="rounded-2xl border border-slate-200/80 bg-white overflow-hidden shadow-xs transition-all"
                >
                  {/* Accordion Header */}
                  <button
                    onClick={() => toggleQuestion(idx)}
                    className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-slate-50/80 transition-colors"
                  >
                    <div className="flex items-start gap-3.5 pr-4">
                      <span className="shrink-0 w-7 h-7 rounded-full bg-slate-100 border border-slate-200/80 text-xs font-mono font-bold flex items-center justify-center text-slate-800 mt-0.5">
                        {qIndex}
                      </span>
                      <div>
                        <h4 className="font-semibold text-sm sm:text-base text-slate-900 leading-snug">
                          {qf.interviewer_question}
                        </h4>
                        <p className="text-xs text-slate-500 line-clamp-1 mt-1">
                          Candidate: &ldquo;{qf.candidate_answer}&rdquo;
                        </p>
                      </div>
                    </div>
                    <div className="shrink-0 flex items-center gap-2">
                      {qComp?.self_score && (
                        <Badge variant="zinc" size="sm" className="hidden sm:inline-flex text-xs">
                          Self: {qComp.self_score}/5
                        </Badge>
                      )}
                      <div className="text-slate-400">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>
                  </button>

                  {/* Accordion Body */}
                  {isExpanded && (
                    <div className="px-5 pb-5 pt-2 border-t border-slate-100 space-y-4 bg-slate-50/40 text-xs sm:text-sm">
                      {/* Candidate Self-Evaluation Comparison */}
                      {qComp && qComp.self_score && (
                        <div className="p-3.5 bg-white rounded-xl border border-slate-200/80 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                              Candidate Self-Evaluation
                            </span>
                            <div className="flex items-center gap-1.5">
                              <Badge variant="zinc" size="sm">Self-Score: {qComp.self_score}/5</Badge>
                              {qComp.self_confidence && (
                                <span className="text-xs text-slate-400">({qComp.self_confidence} confidence)</span>
                              )}
                            </div>
                          </div>
                          {(qComp.self_strengths || qComp.self_missed_points) && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs pt-1 border-t border-slate-100">
                              {qComp.self_strengths && (
                                <div>
                                  <span className="font-medium text-emerald-800">What you felt went well: </span>
                                  <span className="text-slate-600">{qComp.self_strengths}</span>
                                </div>
                              )}
                              {qComp.self_missed_points && (
                                <div>
                                  <span className="font-medium text-amber-800">What you felt was missed: </span>
                                  <span className="text-slate-600">{qComp.self_missed_points}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                      {/* Candidate Quote Highlight */}
                      {qf.verbatim_quote && (
                        <div className="p-3.5 bg-white rounded-xl border border-indigo-200/80 space-y-1.5">
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-800">
                            <Quote className="w-3.5 h-3.5 text-indigo-600" />
                            <span>Verbatim Candidate Quote Highlighted</span>
                          </div>
                          <p className="italic text-slate-800 font-mono text-xs sm:text-sm pl-4 border-l-2 border-indigo-500 leading-relaxed">
                            &ldquo;{qf.verbatim_quote}&rdquo;
                          </p>
                        </div>
                      )}

                      {/* Gilfoyle Critique */}
                      <div className="p-3.5 bg-amber-50/60 rounded-lg border border-amber-200/80 space-y-1.5">
                        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-900">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
                          <span>Evaluation Critique</span>
                        </div>
                        <p className="text-ink leading-relaxed pl-5 text-xs">
                          {qf.critique}
                        </p>
                      </div>

                      {/* What You Could Have Said Better */}
                      <div className="p-4 bg-emerald-50/40 rounded-lg border-2 border-emerald-300/80 space-y-2 shadow-xs">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="p-1 rounded-md bg-emerald-100 text-emerald-800">
                              <Sparkles className="w-4 h-4 text-emerald-700" />
                            </span>
                            <div>
                              <h5 className="font-bold text-xs text-emerald-950">
                                What You Could Have Said Better
                              </h5>
                              <span className="text-[10px] text-emerald-700 font-mono">
                                Staff-Level Engineering Response Formulation
                              </span>
                            </div>
                          </div>
                          <Badge variant="emerald" size="sm" className="font-mono text-[10px]">
                            Model Phrasing
                          </Badge>
                        </div>

                        <div className="p-3 bg-white rounded-md border border-emerald-200 text-xs text-ink leading-relaxed whitespace-pre-wrap font-sans">
                          {qf.strong_answer_guide}
                        </div>
                      </div>

                      {/* Targeted Resource */}
                      {qf.targeted_resource && (
                        <div className="flex items-center gap-2 text-ink-subtle pt-1 text-xs">
                          <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
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

      {/* Complete Interview Transcript Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-900">Complete Stored Interview Transcript</h3>
              <Badge variant="indigo" className="font-mono text-xs">
                {(evaluation.transcript_turns?.length || evaluation.question_feedback?.length || 0)} Turns Recorded
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Persistent archive of candidate responses, verbal dialogue, and interviewer follow-up questions
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopyTranscript}
              className="text-xs flex items-center gap-1.5"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>{copiedTranscript ? 'Copied!' : 'Copy Transcript'}</span>
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleDownloadTranscript}
              className="text-xs flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download (.txt)</span>
            </Button>
          </div>
        </div>

        {/* Turn by turn dialogue list */}
        <div className="space-y-3.5">
          {(evaluation.transcript_turns && evaluation.transcript_turns.length > 0
            ? evaluation.transcript_turns
            : (evaluation.question_feedback && evaluation.question_feedback.length > 0
                ? evaluation.question_feedback.map((q) => ({
                    question_index: q.question_index,
                    interviewer_question: q.interviewer_question,
                    candidate_answer: q.candidate_answer,
                    is_follow_up: false,
                  }))
                : []
              )
          ).map((turn, tIdx) => (
            <Card key={tIdx} className="p-5 space-y-3.5 rounded-2xl border border-slate-200/80 bg-white shadow-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className="text-xs font-mono font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center text-[11px]">
                    {turn.question_index || tIdx + 1}
                  </span>
                  Turn {turn.question_index || tIdx + 1}
                </span>
                {turn.is_follow_up && (
                  <Badge variant="amber" className="text-[10px]">Adaptive Follow-Up</Badge>
                )}
              </div>

              {/* Interviewer Message */}
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="flex-1 bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/60">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Interviewer
                  </span>
                  <p className="text-xs sm:text-sm text-slate-900 leading-relaxed font-sans">
                    {turn.interviewer_question}
                  </p>
                </div>
              </div>

              {/* Candidate Message */}
              <div className="flex items-start gap-3 pl-4 sm:pl-6">
                <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
                <div className="flex-1 bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Candidate Response
                  </span>
                  <p className="text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap font-sans">
                    {turn.candidate_answer || (
                      <span className="italic text-slate-400">No candidate response recorded for this question turn.</span>
                    )}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

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
                  <span className="text-lg font-bold text-indigo-700 font-mono">
                    {dim.ai_score}/5
                  </span>
                </div>
              </div>

              {dim.evidence_quote && (
                <div className="p-3 bg-surface-warm rounded-md border border-surface-border text-xs text-ink-muted flex items-start gap-2 italic">
                  <Quote className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5 not-italic" />
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
