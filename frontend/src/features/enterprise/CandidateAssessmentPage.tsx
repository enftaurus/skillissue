import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../../lib/api';
import { CandidateAssessment } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  Building2,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Code2,
  Boxes,
  Mic,
  ArrowRight,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';

export const CandidateAssessmentPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [assessment, setAssessment] = useState<CandidateAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowBlurs, setWindowBlurs] = useState<number>(0);
  const [showBlurWarning, setShowBlurWarning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Active round state
  const [codeAnswer, setCodeAnswer] = useState<string>(
    '# Write your solution here\ndef solve(nums):\n    # Optimal solution\n    return sorted(nums)\n'
  );
  const [interviewAnswer, setInterviewAnswer] = useState<string>('');
  const [activeQuestion] = useState<string>(
    'Explain the synchronization mechanism you would implement in your rate limiter to ensure accurate request counting under 10,000 req/sec across 4 worker processes.'
  );

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.get<CandidateAssessment>(`/enterprise/assessments/${token}`)
      .then((data) => {
        setAssessment(data);
      })
      .catch((err) => {
        console.error('Failed to load candidate assessment', err);
        setError('Invalid or expired assessment link.');
      })
      .finally(() => setLoading(false));
  }, [token]);

  // Tab switch / blur tracking
  useEffect(() => {
    const handleBlur = () => {
      setWindowBlurs((prev) => {
        const next = prev + 1;
        setShowBlurWarning(true);
        setTimeout(() => setShowBlurWarning(false), 5000);
        return next;
      });
    };

    window.addEventListener('blur', handleBlur);
    return () => window.removeEventListener('blur', handleBlur);
  }, []);

  const handleNextRound = async () => {
    if (!token || !assessment) return;

    const currentRound = assessment.rounds[assessment.current_round_index];
    if (!currentRound) return;

    try {
      setIsSubmitting(true);
      const submissionData: Record<string, any> = {
        code: codeAnswer,
        answer: interviewAnswer,
        score: Math.floor(Math.random() * 15) + 80, // Simulated score between 80-95
      };

      const updated = await api.post<CandidateAssessment>(`/enterprise/assessments/${token}/submit-round`, {
        round_index: assessment.current_round_index,
        round_type: currentRound.round_type,
        submission_data: submissionData,
        integrity_events: {
          window_blurs: windowBlurs,
          copy_paste_count: 1,
        },
      });

      setAssessment(updated);
      setInterviewAnswer('');
    } catch (err) {
      console.error('Failed to submit round', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-warm">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-ink-muted">Loading your secure assessment session...</p>
        </div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-warm p-4">
        <Card className="max-w-md p-8 text-center space-y-4">
          <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
          <h2 className="text-lg font-bold text-ink">Assessment Unavailable</h2>
          <p className="text-xs text-ink-muted">{error || 'Unable to access assessment.'}</p>
        </Card>
      </div>
    );
  }

  const isCompleted = assessment.status === 'completed' || assessment.status === 'flagged';
  const currentRound = assessment.rounds[assessment.current_round_index];

  return (
    <div className="min-h-screen bg-surface-warm flex flex-col font-sans text-ink">
      {/* Integrity Warning Toast */}
      {showBlurWarning && (
        <div className="fixed top-4 right-4 z-50 bg-amber-500 text-ink-inverted px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 text-xs animate-bounce">
          <ShieldAlert className="w-4 h-4 text-white" />
          <span className="font-semibold">
            Warning: Tab blur detected ({windowBlurs} switch{windowBlurs > 1 ? 'es' : ''}). Proctoring logs focus changes.
          </span>
        </div>
      )}

      {/* Top Header */}
      <header className="bg-white border-b border-surface-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center">
            <Building2 className="w-5 h-5 text-ink" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-ink">{assessment.pipeline_title}</h1>
            <p className="text-[11px] text-ink-muted font-mono">
              Candidate: {assessment.candidate_name} ({assessment.target_role})
            </p>
          </div>
        </div>

        {/* Status / Proctoring Pill */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-subtle border border-surface-border text-xs font-mono">
            {windowBlurs > 2 ? (
              <ShieldAlert className="w-3.5 h-3.5 text-red-600" />
            ) : (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            )}
            <span>Proctoring Active ({windowBlurs} blurs)</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl mx-auto w-full p-4 sm:p-8 space-y-6">
        {/* Stage Progress Bar */}
        <div className="grid grid-cols-3 gap-3">
          {assessment.rounds.map((round, idx) => {
            const isDone = idx < assessment.current_round_index;
            const isCurrent = idx === assessment.current_round_index && !isCompleted;

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border text-xs transition-all ${
                  isCurrent
                    ? 'bg-white border-lime-500 shadow-sm'
                    : isDone
                    ? 'bg-lime-50/40 border-lime-500/20 text-lime-900'
                    : 'bg-surface-subtle border-surface-border text-ink-muted'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
                    Stage {idx + 1}
                  </span>
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" />
                  ) : (
                    <span className="text-[10px] font-mono text-ink-subtle">{round.time_limit_minutes}m</span>
                  )}
                </div>
                <p className="font-semibold text-ink mt-1 truncate">{round.name}</p>
              </div>
            );
          })}
        </div>

        {/* Content Box */}
        {isCompleted ? (
          <Card className="p-10 text-center space-y-5 bg-white border border-surface-border">
            <div className="w-16 h-16 rounded-full bg-lime-500/10 border border-lime-500/20 flex items-center justify-center mx-auto text-lime-700">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-ink">Assessment Successfully Completed</h2>
              <p className="text-xs sm:text-sm text-ink-muted max-w-md mx-auto leading-relaxed">
                Your submissions across all stages (DSA OA, Machine Coding, and Oral AI Interview) have been securely logged.
                The hiring team will review your transcripts and performance calibration.
              </p>
            </div>
            <div className="p-4 rounded-xl bg-surface-subtle border border-surface-border inline-block text-xs font-mono">
              <span className="text-ink-subtle">Composite Readiness Score: </span>
              <span className="font-bold text-ink text-sm">{assessment.composite_score}%</span>
            </div>
          </Card>
        ) : (
          <Card className="p-6 sm:p-8 space-y-6 bg-white border border-surface-border">
            {/* Round 1: OA DSA Coding */}
            {currentRound?.round_type === 'oa_dsa' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-surface-border">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-5 h-5 text-lime-600" />
                    <div>
                      <h2 className="font-bold text-base text-ink">Stage 1: Algorithmic OA Challenge</h2>
                      <p className="text-xs text-ink-muted">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    2 Questions • Python / Java / C++
                  </Badge>
                </div>

                <div className="bg-surface-subtle p-4 rounded-lg border border-surface-border text-xs text-ink space-y-2">
                  <p className="font-semibold">Problem: Alien Dictionary Ordering</p>
                  <p className="text-ink-muted leading-relaxed">
                    Given a sorted dictionary of an alien language, derive the lexicographical order of letters.
                    Return an empty string if cycles or invalid orderings are detected.
                  </p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink">Your Code Implementation:</label>
                  <textarea
                    rows={8}
                    value={codeAnswer}
                    onChange={(e) => setCodeAnswer(e.target.value)}
                    className="w-full font-mono text-xs p-3 rounded-lg border border-surface-border bg-slate-50 focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Round 2: Machine Coding Take-Home */}
            {currentRound?.round_type === 'ai_project' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-surface-border">
                  <div className="flex items-center gap-2">
                    <Boxes className="w-5 h-5 text-indigo-600" />
                    <div>
                      <h2 className="font-bold text-base text-ink">Stage 2: AI-Assisted Machine Coding Project</h2>
                      <p className="text-xs text-ink-muted">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    Read-Only Copilot • Prompt Grader
                  </Badge>
                </div>

                <div className="bg-surface-subtle p-4 rounded-lg border border-surface-border text-xs text-ink space-y-2">
                  <p className="font-semibold">Task: Distributed Rate Limiter Simulation</p>
                  <p className="text-ink-muted leading-relaxed">
                    Implement a token-bucket rate limiter that coordinates across workers.
                    You may query the read-only AI Copilot for architecture advice, but prompt clarity and engineering precision are graded.
                  </p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink">Implementation / Architectural Notes:</label>
                  <textarea
                    rows={8}
                    value={codeAnswer}
                    onChange={(e) => setCodeAnswer(e.target.value)}
                    placeholder="Enter your implementation code and concurrency handling primitives..."
                    className="w-full font-mono text-xs p-3 rounded-lg border border-surface-border bg-slate-50 focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Round 3: Tough AI Oral Interview */}
            {currentRound?.round_type === 'tough_interview' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-surface-border">
                  <div className="flex items-center gap-2">
                    <Mic className="w-5 h-5 text-amber-600" />
                    <div>
                      <h2 className="font-bold text-base text-ink">Stage 3: Anti-Sycophancy Technical Defense</h2>
                      <p className="text-xs text-ink-muted">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    Adaptive Probing • Zero Generic Praise
                  </Badge>
                </div>

                <div className="bg-lime-50/50 p-4 rounded-lg border border-lime-500/20 text-xs text-ink space-y-2">
                  <p className="font-bold text-lime-900 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-lime-700" />
                    Interviewer Question:
                  </p>
                  <p className="text-ink-muted font-medium leading-relaxed">&ldquo;{activeQuestion}&rdquo;</p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-ink">Your Spoken / Written Technical Answer:</label>
                  <textarea
                    rows={6}
                    value={interviewAnswer}
                    onChange={(e) => setInterviewAnswer(e.target.value)}
                    placeholder="Provide specific implementation details, trade-offs, and benchmarks..."
                    className="w-full text-xs p-3 rounded-lg border border-surface-border focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Submit Action */}
            <div className="pt-4 border-t border-surface-border flex items-center justify-between">
              <span className="text-[11px] text-ink-subtle font-mono">
                {assessment.current_round_index + 1} of {assessment.rounds.length} Stages
              </span>
              <Button
                onClick={handleNextRound}
                disabled={isSubmitting}
                className="gap-2 bg-ink text-white hover:bg-ink/90 text-xs font-semibold"
              >
                <span>{assessment.current_round_index === assessment.rounds.length - 1 ? 'Finish Assessment' : 'Complete Stage & Next'}</span>
                <ArrowRight className="w-3.5 h-3.5 text-lime-400" />
              </Button>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
};
