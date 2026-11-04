import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../../lib/api';
import { CandidateAssessment } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
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
  FileText,
  UserCheck,
  HelpCircle,
} from 'lucide-react';
import { useEditorTelemetry } from '../../lib/useEditorTelemetry';
import { ExplanationCheckModal } from '../coding/ExplanationCheckModal';

export const CandidateAssessmentPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [assessment, setAssessment] = useState<CandidateAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowBlurs, setWindowBlurs] = useState<number>(0);
  const [showBlurWarning, setShowBlurWarning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showExplanationModal, setShowExplanationModal] = useState<boolean>(false);
  const [activeCheckRoundKey, setActiveCheckRoundKey] = useState<string>('0');
  const [activeCheckTitle, setActiveCheckTitle] = useState<string>('Algorithmic Online Assessment');
  const [pendingAssessmentUpdate, setPendingAssessmentUpdate] = useState<CandidateAssessment | null>(null);

  // Candidate Intake Form State
  const [candidateNameInput, setCandidateNameInput] = useState<string>('');
  const [candidateEmailInput, setCandidateEmailInput] = useState<string>('');
  const [entryError, setEntryError] = useState<string | null>(null);

  // Resume Intake
  const [candidateResume, setCandidateResume] = useState<string>('');

  // Active round state
  const [codeAnswer, setCodeAnswer] = useState<string>(
    '# Write your solution here\ndef solve(words):\n    # Optimal topological sort / Alien dictionary ordering\n    adj = {}\n    in_degree = {}\n    # Construct graph\n    return ""\n'
  );
  const [interviewAnswer, setInterviewAnswer] = useState<string>('');
  const [activeQuestion] = useState<string>(
    'Walk me through the exact algorithm you wrote in Stage 1. Why did you choose Kahn\'s algorithm or DFS topological sort, and what is its big-O space complexity on cyclic test inputs?'
  );

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    api.get<CandidateAssessment>(`/enterprise/assessments/${token}`)
      .then((data) => {
        setAssessment(data);
        if (data.resume_text) {
          setCandidateResume(data.resume_text);
        }
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

  const handleEnterAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !candidateNameInput.trim() || !candidateEmailInput.trim()) return;

    try {
      setIsSubmitting(true);
      setEntryError(null);
      const entered = await api.post<CandidateAssessment>(
        `/enterprise/assessments/entry/${token}`,
        {
          candidate_name: candidateNameInput.trim(),
          candidate_email: candidateEmailInput.trim(),
        }
      );
      setAssessment(entered);
      if (entered.resume_text) {
        setCandidateResume(entered.resume_text);
      }
    } catch (err: any) {
      console.error('Failed to enter assessment', err);
      setEntryError(err?.response?.data?.detail || 'Failed to enter assessment. Check credentials or link expiration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentRoundIndex = assessment?.current_round_index ?? 0;
  const currentRound = assessment?.rounds?.[currentRoundIndex];
  const isCodingRound = currentRound?.round_type === 'oa_dsa' || currentRound?.round_type === 'ai_project';

  const { logContentChange, logKeyDown, logPaste, flushQueue } = useEditorTelemetry({
    roundKey: String(currentRoundIndex),
    candidateToken: assessment?.access_token || token,
    enabled: Boolean(assessment?.access_token && isCodingRound),
  });

  const handleNextRound = async () => {
    if (!token || !assessment) return;
    const round = assessment.rounds[assessment.current_round_index];
    if (!round) return;

    try {
      setIsSubmitting(true);
      // Flush editor telemetry batch before submission
      if (isCodingRound) {
        await flushQueue();
      }

      const submissionData: Record<string, any> = {
        code: codeAnswer,
        answer: interviewAnswer,
      };

      const payload: Record<string, any> = {
        round_index: assessment.current_round_index,
        round_type: round.round_type,
        submission_data: submissionData,
        integrity_events: {
          window_blurs: windowBlurs,
          copy_paste_count: 1,
        },
      };

      if (candidateResume.trim()) {
        payload.resume_text = candidateResume.trim();
      }

      if (round.round_type === 'oa_dsa') {
        payload.oa_problem_title = 'Alien Dictionary & Topological Sort';
        payload.oa_submitted_code = codeAnswer;
      }

      const submittedRoundIndex = assessment.current_round_index;
      const submittedRoundName = round.name;

      const subToken = assessment.access_token || token;
      const updated = await api.post<CandidateAssessment>(
        `/enterprise/assessments/${subToken}/submit-round`,
        payload
      );

      // If it's a coding round, trigger post-code explanation check cross-examination
      if (round.round_type === 'oa_dsa' || round.round_type === 'ai_project') {
        setActiveCheckRoundKey(String(submittedRoundIndex));
        setActiveCheckTitle(submittedRoundName || 'Algorithmic Online Assessment');
        setPendingAssessmentUpdate(updated);
        setShowExplanationModal(true);
      } else {
        setAssessment(updated);
        setInterviewAnswer('');
      }
    } catch (err) {
      console.error('Failed to submit round', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExplanationComplete = () => {
    setShowExplanationModal(false);
    if (pendingAssessmentUpdate) {
      setAssessment(pendingAssessmentUpdate);
      setPendingAssessmentUpdate(null);
    }
    setInterviewAnswer('');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-zinc-500 font-mono">Connecting to secure proctored assessment runner...</p>
        </div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 p-4">
        <Card className="max-w-md p-8 text-center space-y-4 rounded-2xl border-zinc-200 bg-white">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-zinc-900">Assessment Unavailable</h2>
          <p className="text-xs text-zinc-500">{error || 'Unable to access assessment.'}</p>
        </Card>
      </div>
    );
  }

  const isEntryRequired = assessment.status === 'entry_required' || !assessment.access_token;
  const isCompleted = assessment.status === 'completed' || assessment.status === 'flagged';

  return (
    <div className="min-h-screen bg-zinc-50/60 flex flex-col font-sans text-zinc-900">
      {/* Integrity Warning Toast */}
      {showBlurWarning && (
        <div className="fixed top-4 right-4 z-50 bg-amber-500 text-white px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 text-xs animate-bounce font-medium">
          <ShieldAlert className="w-4 h-4 text-white" />
          <span>
            Warning: Browser tab focus change logged ({windowBlurs} blurs). Anti-cheating proctoring active.
          </span>
        </div>
      )}

      {/* Top Header */}
      <header className="bg-white border-b border-zinc-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900">
            <Building2 className="w-5 h-5 text-zinc-900" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-zinc-950">{assessment.pipeline_title || 'Campus Hiring Assessment'}</h1>
            <p className="text-[11px] text-zinc-500 font-mono">
              {isEntryRequired
                ? `Role: ${assessment.target_role || 'Engineering Candidate'}`
                : `Candidate: ${assessment.candidate_name} (${assessment.target_role})`}
            </p>
          </div>
        </div>

        {/* Status / Proctoring Pill */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-zinc-50 border border-zinc-200 text-xs font-mono">
            {isEntryRequired ? (
              <>
                <UserCheck className="w-3.5 h-3.5 text-lime-600" />
                <span>Candidate Verification</span>
              </>
            ) : windowBlurs > 2 ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                <span>Proctoring ({windowBlurs} switches)</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Proctoring Active</span>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-5xl mx-auto w-full p-4 sm:p-8 space-y-6">
        {isEntryRequired ? (
          <Card className="max-w-lg mx-auto p-8 space-y-6 bg-white border border-zinc-200 rounded-2xl shadow-xs">
            <div className="space-y-2 text-center">
              <div className="w-12 h-12 rounded-2xl bg-lime-50 border border-lime-200 flex items-center justify-center mx-auto text-lime-700">
                <UserCheck className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-bold text-zinc-950">Candidate Intake &amp; Identity Verification</h2>
              <p className="text-xs text-zinc-600 leading-relaxed">
                You have been invited to complete the <strong>{assessment.pipeline_title}</strong> assessment for <strong>{assessment.target_role}</strong>. Please enter your full name and official email to begin.
              </p>
            </div>

            {entryError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center gap-2 font-medium">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{entryError}</span>
              </div>
            )}

            <form onSubmit={handleEnterAssessment} className="space-y-4">
              <Input
                label="Full Name"
                placeholder="e.g. John Doe"
                value={candidateNameInput}
                onChange={(e) => setCandidateNameInput(e.target.value)}
                required
              />

              <Input
                label="Email Address"
                type="email"
                placeholder="e.g. student@university.edu"
                value={candidateEmailInput}
                onChange={(e) => setCandidateEmailInput(e.target.value)}
                required
              />

              <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200 text-[11px] text-zinc-600 space-y-1">
                <p className="font-semibold text-zinc-800">Assessment Protocol:</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  <li>{assessment.rounds.length} stages (OA coding, systems design/project, oral interview)</li>
                  <li>Link valid for 7 days once activated</li>
                  <li>Anti-cheating window focus monitoring instrumented</li>
                </ul>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting || !candidateNameInput.trim() || !candidateEmailInput.trim()}
                className="w-full bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold py-2.5 rounded-xl gap-2"
              >
                <span>{isSubmitting ? 'Verifying & Generating Token...' : 'Start Assessment'}</span>
                <ArrowRight className="w-4 h-4 text-lime-400" />
              </Button>
            </form>
          </Card>
        ) : (
          <>
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
                        ? 'bg-lime-50/50 border-lime-200 text-lime-900 font-medium'
                        : 'bg-zinc-100/60 border-zinc-200 text-zinc-400'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] font-bold uppercase tracking-wider">
                        Stage {idx + 1}
                      </span>
                      {isDone ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" />
                      ) : (
                        <span className="text-[10px] font-mono text-zinc-400">{round.time_limit_minutes}m</span>
                      )}
                    </div>
                    <p className="font-semibold text-zinc-900 mt-1 truncate">{round.name}</p>
                  </div>
                );
              })}
            </div>

            {/* Content Box */}
            {isCompleted ? (
              <Card className="p-10 text-center space-y-5 bg-white border border-zinc-200 rounded-2xl shadow-xs">
                <div className="w-16 h-16 rounded-full bg-lime-50 border border-lime-200 flex items-center justify-center mx-auto text-lime-700">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-zinc-950">Assessment Successfully Completed</h2>
                  <p className="text-xs sm:text-sm text-zinc-600 max-w-md mx-auto leading-relaxed">
                    Your submissions across all stages (OA Coding, Take-Home Simulation, and Oral Cross-Exam Interview) have been securely logged and analyzed.
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-zinc-50 border border-zinc-200 inline-block text-xs font-mono">
                  <span className="text-zinc-500">Composite Readiness Score: </span>
                  <span className="font-bold text-lime-700 text-sm">
                    {assessment.composite_score != null ? `${assessment.composite_score}%` : 'Pending Evaluation / Unscored'}
                  </span>
                </div>
              </Card>
            ) : (
              <Card className="p-6 sm:p-8 space-y-6 bg-white border border-zinc-200 rounded-2xl shadow-xs">
            {/* Optional Candidate Resume Intake on Stage 1 */}
            {assessment.current_round_index === 0 && (
              <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-200 space-y-2">
                <label className="text-xs font-bold text-zinc-900 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-zinc-700" />
                  Candidate Resume &amp; Projects Intake (Optional)
                </label>
                <textarea
                  rows={3}
                  value={candidateResume}
                  onChange={(e) => setCandidateResume(e.target.value)}
                  placeholder="Paste your resume summary, tech skills, and key projects so the AI interviewer cross-examines your real background in Stage 3..."
                  className="w-full text-xs p-3 rounded-lg border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-lime-500"
                />
              </div>
            )}

            {/* Round 1: OA DSA Coding */}
            {currentRound?.round_type === 'oa_dsa' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <Code2 className="w-5 h-5 text-lime-600" />
                    <div>
                      <h2 className="font-bold text-base text-zinc-950">Stage 1: Algorithmic Online Assessment</h2>
                      <p className="text-xs text-zinc-500">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    Anti-Cheat Instrumented • Python / Java / C++
                  </Badge>
                </div>

                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200 text-xs text-zinc-900 space-y-2">
                  <p className="font-semibold text-zinc-950">Problem: Alien Dictionary Ordering &amp; Cycle Detection</p>
                  <p className="text-zinc-600 leading-relaxed">
                    Given a sorted dictionary of words from an alien language, derive the lexicographical order of letters.
                    Return an empty string if cycles or invalid orderings are detected. Your submitted solution will be orally cross-examined in Stage 3.
                  </p>
                </div>

                {/* Pre-Round Explanation Check Notice */}
                <div className="p-3.5 bg-lime-50/70 border border-lime-200 rounded-xl text-xs text-lime-900 flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-lime-700 shrink-0 mt-0.5" />
                  <div className="space-y-0.5 leading-relaxed">
                    <p className="font-semibold">Post-Code Cross-Examination Notice</p>
                    <p className="text-lime-800 text-[11px]">
                      After submitting your solution, you will answer 3 short follow-up questions grounded in your exact implementation. You can answer briefly via text or voice.
                    </p>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800">Your Code Implementation:</label>
                  <textarea
                    rows={9}
                    value={codeAnswer}
                    onChange={(e) => {
                      const nextVal = e.target.value;
                      logContentChange(nextVal, codeAnswer, e.target.selectionStart || 0, 'typing');
                      setCodeAnswer(nextVal);
                    }}
                    onKeyDown={(e) => logKeyDown(e)}
                    onPaste={(e) => {
                      const text = e.clipboardData.getData('text');
                      logPaste(text, e.currentTarget.selectionStart || 0);
                    }}
                    className="w-full font-mono text-xs p-3 rounded-xl border border-zinc-200 bg-zinc-900 text-lime-400 focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Round 2: Machine Coding Take-Home */}
            {currentRound?.round_type === 'ai_project' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <Boxes className="w-5 h-5 text-indigo-600" />
                    <div>
                      <h2 className="font-bold text-base text-zinc-950">Stage 2: Systems Coding Project (Take-Home Simulation)</h2>
                      <p className="text-xs text-zinc-500">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    Read-Only Copilot • Prompt Grader
                  </Badge>
                </div>

                <div className="bg-zinc-50 p-4 rounded-xl border border-zinc-200 text-xs text-zinc-900 space-y-2">
                  <p className="font-semibold text-zinc-950">Task: High-Throughput Token Bucket Rate Limiter</p>
                  <p className="text-zinc-600 leading-relaxed">
                    Implement a token-bucket rate limiter that coordinates across workers.
                    Prompt engineering clarity and thread-safety architecture are evaluated.
                  </p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800">Implementation / Architectural Notes:</label>
                  <textarea
                    rows={8}
                    value={codeAnswer}
                    onChange={(e) => {
                      const nextVal = e.target.value;
                      logContentChange(nextVal, codeAnswer, e.target.selectionStart || 0, 'typing');
                      setCodeAnswer(nextVal);
                    }}
                    onKeyDown={(e) => logKeyDown(e)}
                    onPaste={(e) => {
                      const text = e.clipboardData.getData('text');
                      logPaste(text, e.currentTarget.selectionStart || 0);
                    }}
                    placeholder="Enter your implementation code and concurrency handling primitives..."
                    className="w-full font-mono text-xs p-3 rounded-xl border border-zinc-200 bg-zinc-900 text-lime-400 focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Round 3: Tough AI Oral Interview with Cross-Examination */}
            {currentRound?.round_type === 'tough_interview' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                  <div className="flex items-center gap-2">
                    <Mic className="w-5 h-5 text-amber-600" />
                    <div>
                      <h2 className="font-bold text-base text-zinc-950">Stage 3: Anti-Sycophancy Oral Cross-Examination</h2>
                      <p className="text-xs text-zinc-500">Time Limit: {currentRound.time_limit_minutes} Minutes</p>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-[11px] bg-amber-50 text-amber-900 border-amber-200">
                    Cheating Cross-Examination Active
                  </Badge>
                </div>

                {/* Cross Examination Context Banner */}
                <div className="bg-amber-50/70 p-4 rounded-xl border border-amber-200 text-xs space-y-1.5">
                  <div className="flex items-center gap-2 text-amber-900 font-bold">
                    <ShieldAlert className="w-4 h-4 text-amber-700" />
                    <span>Anti-Cheating Cross-Examination on Stage 1 OA Code</span>
                  </div>
                  <p className="text-amber-800 leading-relaxed">
                    The interviewer is inspecting your submitted Stage 1 code ({assessment.oa_problem_title || 'Alien Dictionary'}). You will be asked to verbally walk through the algorithmic decisions, time complexity, and edge cases to prove authorship.
                  </p>
                </div>

                <div className="bg-lime-50/50 p-4 rounded-xl border border-lime-200 text-xs text-zinc-900 space-y-2">
                  <p className="font-bold text-lime-900 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-lime-700" />
                    Interviewer Question:
                  </p>
                  <p className="text-zinc-700 font-medium leading-relaxed">&ldquo;{activeQuestion}&rdquo;</p>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-800">Your Spoken / Written Technical Answer:</label>
                  <textarea
                    rows={6}
                    value={interviewAnswer}
                    onChange={(e) => setInterviewAnswer(e.target.value)}
                    placeholder="Provide specific implementation details, trade-offs, and explain your submitted code..."
                    className="w-full text-xs p-3 rounded-xl border border-zinc-200 focus:outline-none focus:ring-1 focus:ring-lime-500"
                  />
                </div>
              </div>
            )}

            {/* Submit Action */}
            <div className="pt-4 border-t border-zinc-100 flex items-center justify-between">
              <span className="text-[11px] text-zinc-500 font-mono">
                Stage {assessment.current_round_index + 1} of {assessment.rounds.length}
              </span>
              <Button
                onClick={handleNextRound}
                disabled={isSubmitting}
                className="gap-2 bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold rounded-xl"
              >
                <span>{assessment.current_round_index === assessment.rounds.length - 1 ? 'Finish Assessment' : 'Complete Stage & Next'}</span>
                <ArrowRight className="w-3.5 h-3.5 text-lime-400" />
              </Button>
            </div>
          </Card>
        )}
        </>
      )}

      {/* Post-Code Submission Cross-Examination Modal */}
      {assessment && (
        <ExplanationCheckModal
          isOpen={showExplanationModal}
          mode="assessment"
          submissionRef={`oa_round_${activeCheckRoundKey}`}
          roundKey={activeCheckRoundKey}
          problemTitle={activeCheckTitle}
          candidateAssessmentId={assessment.id}
          candidateToken={assessment.access_token || token}
          onComplete={handleExplanationComplete}
          onClose={() => setShowExplanationModal(false)}
        />
      )}
    </main>
    </div>
  );
};
