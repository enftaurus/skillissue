import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../lib/api';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { SpeechHandler } from '../../lib/speech';
import {
  HelpCircle,
  Clock,
  Mic,
  MicOff,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Code2,
  FileQuestion,
  ShieldCheck,
  ChevronRight,
  Info,
} from 'lucide-react';

export interface ExplanationCheckQuestion {
  type: 'rationale' | 'mutation' | 'behaviour';
  text: string;
  code_reference: string;
}

export interface ExplanationCheckAnswer {
  question_index: number;
  text: string;
  input_mode: 'text' | 'voice';
  seconds_to_first_input?: number;
}

export interface QuestionEvaluation {
  question_index: number;
  accuracy: number;
  consistency: number;
  depth: number;
  evidence_quote?: string;
  code_reference?: string;
  critique?: string;
}

export interface ExplanationEvaluation {
  explanation_consistency: number;
  avg_accuracy?: number;
  avg_depth?: number;
  question_evaluations: QuestionEvaluation[];
  coaching_what_went_well?: string[];
  coaching_what_to_revisit?: string[];
}

export interface ExplanationCheckData {
  id: string;
  round_key: string;
  mode: 'practice' | 'assessment';
  status: 'pending' | 'answered' | 'evaluated' | 'not_evaluated' | 'insufficient_data';
  questions: ExplanationCheckQuestion[];
  discriminative_power?: 'low' | 'normal';
  evaluation?: ExplanationEvaluation | null;
  confidence?: 'low' | 'medium' | 'high' | null;
}

interface ExplanationCheckModalProps {
  isOpen: boolean;
  mode: 'practice' | 'assessment';
  submissionRef: string;
  roundKey: string;
  problemTitle: string;
  candidateAssessmentId?: string;
  candidateToken?: string;
  onComplete: () => void;
  onClose: () => void;
}

const DEFAULT_TIME_LIMIT_SECONDS = 90;

export const ExplanationCheckModal: React.FC<ExplanationCheckModalProps> = ({
  isOpen,
  mode,
  submissionRef,
  roundKey,
  problemTitle,
  candidateAssessmentId,
  candidateToken,
  onComplete,
  onClose,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [checkData, setCheckData] = useState<ExplanationCheckData | null>(null);

  // Active question index
  const [currentQIndex, setCurrentQIndex] = useState<number>(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [currentAnswer, setCurrentAnswer] = useState<string>('');
  const [secondsLeft, setSecondsLeft] = useState<number>(DEFAULT_TIME_LIMIT_SECONDS);
  const [questionStartTime, setQuestionStartTime] = useState<number>(Date.now());
  const [firstInputSeconds, setFirstInputSeconds] = useState<Record<number, number>>({});

  // Voice recording state
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const speechHandlerRef = useRef<SpeechHandler | null>(null);

  // Completed / Evaluation view
  const [isFinished, setIsFinished] = useState<boolean>(false);

  // Auth headers
  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {};
    if (candidateToken) {
      headers['Authorization'] = `Bearer ${candidateToken}`;
    }
    return headers;
  };

  // 1. Initialize Explanation Check
  useEffect(() => {
    if (!isOpen) {
      setCheckData(null);
      setIsFinished(false);
      setCurrentQIndex(0);
      setAnswers({});
      setCurrentAnswer('');
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      submission_ref: submissionRef,
      mode,
      candidate_assessment_id: candidateAssessmentId || null,
      round_key: roundKey,
      problem_title: problemTitle,
    };

    api.post<ExplanationCheckData>('/explanation-checks', payload, { headers: getAuthHeaders() })
      .then((data) => {
        setCheckData(data);
        if (data.status === 'evaluated' || data.status === 'answered') {
          setIsFinished(true);
        } else {
          setSecondsLeft(DEFAULT_TIME_LIMIT_SECONDS);
          setQuestionStartTime(Date.now());
        }
      })
      .catch((err) => {
        console.error('Failed to create explanation check', err);
        setError('Unable to initialize cross-examination follow-up. Please check connection.');
      })
      .finally(() => setLoading(false));
  }, [isOpen, submissionRef, mode, candidateAssessmentId, roundKey, problemTitle]);

  // 2. Countdown Timer
  useEffect(() => {
    if (!isOpen || isFinished || loading || !checkData || checkData.status !== 'pending') return;

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          // Time expired for this question, auto-advance
          handleNextQuestion(true);
          return DEFAULT_TIME_LIMIT_SECONDS;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, isFinished, loading, checkData, currentQIndex, currentAnswer]);

  // 3. Speech Recognition Setup
  useEffect(() => {
    speechHandlerRef.current = new SpeechHandler(
      (text: string) => {
        if (text) {
          setCurrentAnswer((prev) => (prev ? `${prev} ${text}` : text));
          recordFirstInput();
        }
      },
      (err: string) => {
        console.warn('Speech error:', err);
        setIsRecording(false);
      },
      (listening: boolean) => {
        setIsRecording(listening);
      }
    );

    return () => {
      speechHandlerRef.current?.stop();
    };
  }, []);

  const recordFirstInput = () => {
    if (firstInputSeconds[currentQIndex] === undefined) {
      const elapsed = (Date.now() - questionStartTime) / 1000.0;
      setFirstInputSeconds((prev) => ({ ...prev, [currentQIndex]: Number(elapsed.toFixed(1)) }));
    }
  };

  const toggleRecording = () => {
    if (!speechHandlerRef.current) return;
    if (isRecording) {
      speechHandlerRef.current.stop();
    } else {
      speechHandlerRef.current.start();
    }
  };

  const handleNextQuestion = (forcedByTimeout = false) => {
    if (!checkData) return;

    // Stop recording if active
    if (isRecording) {
      speechHandlerRef.current?.stop();
    }

    const trimmedAnswer = currentAnswer.trim() || (forcedByTimeout ? '[Time limit expired]' : '');
    const updatedAnswers = { ...answers, [currentQIndex]: trimmedAnswer };
    setAnswers(updatedAnswers);

    const nextIdx = currentQIndex + 1;
    if (nextIdx < checkData.questions.length) {
      setCurrentQIndex(nextIdx);
      setCurrentAnswer(updatedAnswers[nextIdx] || '');
      setSecondsLeft(DEFAULT_TIME_LIMIT_SECONDS);
      setQuestionStartTime(Date.now());
    } else {
      // All questions answered, submit payload
      handleSubmitAllAnswers(updatedAnswers);
    }
  };

  const handleSubmitAllAnswers = async (finalAnswers: Record<number, string>) => {
    if (!checkData) return;
    setSubmitting(true);
    setError(null);

    const payloadAnswers: ExplanationCheckAnswer[] = checkData.questions.map((_, idx) => ({
      question_index: idx,
      text: finalAnswers[idx] || '',
      input_mode: 'text',
      seconds_to_first_input: firstInputSeconds[idx] || 5.0,
    }));

    try {
      const updated = await api.post<ExplanationCheckData>(
        `/explanation-checks/${checkData.id}/answers`,
        { answers: payloadAnswers },
        { headers: getAuthHeaders() }
      );
      setCheckData((prev) => (prev ? { ...prev, ...updated } : updated));
      setIsFinished(true);
    } catch (err: any) {
      console.error('Failed to submit explanation answers', err);
      setError(err?.response?.data?.detail || 'Failed to submit answers. Time limit may have expired.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const currentQ = checkData?.questions?.[currentQIndex];
  const totalQuestions = checkData?.questions?.length || 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl border border-zinc-200 shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-lime-100 border border-lime-300 flex items-center justify-center text-lime-800">
              <FileQuestion className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-zinc-950">
                  {mode === 'assessment' ? 'Post-Submission Cross-Examination' : 'Code Explanation Check & Coaching'}
                </h3>
                {checkData?.discriminative_power === 'low' && (
                  <Badge variant="outline" className="text-[10px] font-mono text-zinc-500">
                    Brief Solution
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-500 font-mono truncate max-w-md">
                Problem: {problemTitle || 'Coding Challenge'}
              </p>
            </div>
          </div>

          {!isFinished && checkData && (
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold border ${
              secondsLeft <= 15
                ? 'bg-rose-50 border-rose-300 text-rose-700 animate-pulse'
                : 'bg-zinc-100 border-zinc-200 text-zinc-700'
            }`}>
              <Clock className="w-3.5 h-3.5" />
              <span>{secondsLeft}s</span>
            </div>
          )}
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs sm:text-sm">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-7 h-7 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-zinc-500 font-mono">Analyzing submitted code structure &amp; generating grounded questions...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 space-y-2">
              <div className="flex items-center gap-2 font-bold text-xs">
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Explanation Check Notice</span>
              </div>
              <p className="text-xs leading-relaxed">{error}</p>
              <div className="pt-2">
                <Button size="sm" variant="outline" onClick={onClose} className="text-xs">
                  Close
                </Button>
              </div>
            </div>
          ) : isFinished ? (
            /* Finished Stage */
            <div className="space-y-6">
              {mode === 'practice' ? (
                /* Practice Mode Coaching Feedback */
                <div className="space-y-5">
                  <div className="p-5 rounded-2xl bg-lime-50/70 border border-lime-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-lime-900 font-bold text-sm">
                        <Sparkles className="w-4 h-4 text-lime-700" />
                        <span>Explanation Feedback &amp; Review</span>
                      </div>
                      <Badge variant="outline" className="font-mono bg-white text-lime-800 border-lime-300">
                        Consistency: {Math.round((checkData?.evaluation?.explanation_consistency || 0) * 100)}%
                      </Badge>
                    </div>
                    <p className="text-xs text-lime-800/90 leading-relaxed">
                      Your spoken/written explanation was evaluated against your submitted code to assess architectural reasoning, edge case comprehension, and computational clarity.
                    </p>
                  </div>

                  {/* What Went Well */}
                  {checkData?.evaluation?.coaching_what_went_well && checkData.evaluation.coaching_what_went_well.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        Key Strengths Identified
                      </h4>
                      <ul className="space-y-1.5 pl-5 list-disc text-xs text-zinc-700">
                        {checkData.evaluation.coaching_what_went_well.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* What To Revisit */}
                  {checkData?.evaluation?.coaching_what_to_revisit && checkData.evaluation.coaching_what_to_revisit.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-bold text-zinc-900 text-xs flex items-center gap-1.5">
                        <HelpCircle className="w-4 h-4 text-amber-600" />
                        Concepts &amp; Trade-offs to Revisit
                      </h4>
                      <ul className="space-y-1.5 pl-5 list-disc text-xs text-zinc-700">
                        {checkData.evaluation.coaching_what_to_revisit.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Per Question Breakdown */}
                  <div className="space-y-3 pt-2">
                    <h4 className="font-bold text-zinc-900 text-xs">Question-by-Question Critique:</h4>
                    <div className="space-y-2.5">
                      {checkData?.evaluation?.question_evaluations?.map((qEval, idx) => {
                        const qObj = checkData.questions[qEval.question_index];
                        return (
                          <div key={idx} className="p-3.5 bg-zinc-50 border border-zinc-200 rounded-xl space-y-2">
                            <div className="flex items-start justify-between gap-2">
                              <span className="font-semibold text-zinc-900 text-xs">
                                Q{idx + 1}: {qObj?.text || 'Code Question'}
                              </span>
                              <Badge variant="outline" className="font-mono text-[10px] shrink-0">
                                Depth {qEval.depth}/4
                              </Badge>
                            </div>
                            {qEval.critique && (
                              <p className="text-xs text-zinc-600 italic">"{qEval.critique}"</p>
                            )}
                            {qEval.code_reference && (
                              <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-200/60 font-mono text-[10px] text-zinc-700">
                                <Code2 className="w-3 h-3" />
                                <span>Ref: {qEval.code_reference}</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                /* Assessment Mode Confirmation (Neutral, Rule 3 compliant) */
                <div className="py-8 text-center space-y-4">
                  <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 mx-auto">
                    <ShieldCheck className="w-8 h-8" />
                  </div>
                  <div className="space-y-1.5">
                    <h3 className="font-bold text-base text-zinc-950">Cross-Examination Responses Recorded</h3>
                    <p className="text-xs text-zinc-600 max-w-md mx-auto leading-relaxed">
                      Your technical responses have been saved and attached to your assessment portfolio. The hiring team reviews your algorithmic rationale alongside your code implementation.
                    </p>
                  </div>
                  <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-xl max-w-sm mx-auto text-[11px] text-zinc-500 font-mono">
                    Session ref: {checkData?.id?.slice(0, 16)}... • Status: Complete
                  </div>
                </div>
              )}
            </div>
          ) : currentQ ? (
            /* Active Question Flow */
            <div className="space-y-5">
              {/* Step indicator */}
              <div className="flex items-center justify-between pb-2 border-b border-zinc-100">
                <span className="font-mono text-xs font-semibold text-zinc-500">
                  Question {currentQIndex + 1} of {totalQuestions}
                </span>
                <div className="flex items-center gap-1.5">
                  <Badge variant="outline" className="font-mono text-[10px] capitalize bg-zinc-50">
                    Type: {currentQ.type}
                  </Badge>
                  {currentQ.code_reference && (
                    <Badge variant="outline" className="font-mono text-[10px] text-lime-800 bg-lime-50 border-lime-200 flex items-center gap-1">
                      <Code2 className="w-3 h-3 text-lime-700" />
                      <span>{currentQ.code_reference}</span>
                    </Badge>
                  )}
                </div>
              </div>

              {/* Prompt box */}
              <div className="p-4 bg-zinc-50 rounded-xl border border-zinc-200 space-y-2">
                <h4 className="font-bold text-zinc-950 text-sm leading-snug">
                  {currentQ.text}
                </h4>
                <p className="text-[11px] text-zinc-500 flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span>Answer briefly in 1-3 sentences. Focus on algorithmic mechanics, not grammar or accent.</span>
                </p>
              </div>

              {/* Answer Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-zinc-800">Your Technical Explanation:</label>
                  <Button
                    type="button"
                    size="sm"
                    variant={isRecording ? 'danger' : 'outline'}
                    onClick={toggleRecording}
                    className="gap-1.5 text-xs font-mono h-7 px-2.5"
                  >
                    {isRecording ? (
                      <>
                        <MicOff className="w-3.5 h-3.5 animate-pulse" />
                        <span>Stop Voice</span>
                      </>
                    ) : (
                      <>
                        <Mic className="w-3.5 h-3.5 text-lime-700" />
                        <span>Speak Answer</span>
                      </>
                    )}
                  </Button>
                </div>

                <textarea
                  rows={4}
                  value={currentAnswer}
                  onChange={(e) => {
                    setCurrentAnswer(e.target.value);
                    recordFirstInput();
                  }}
                  placeholder="Explain why you chose this data structure, how it handles cycles, or what lines would mutate under streaming constraints..."
                  className="w-full text-xs p-3.5 rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-lime-500 leading-relaxed font-sans"
                  autoFocus
                />
              </div>

              {/* Notice */}
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-200/80 text-[11px] text-zinc-500 leading-relaxed">
                {mode === 'assessment'
                  ? 'Your answers are evaluated alongside your code for comprehension and consistency. Time limit is 90 seconds per question.'
                  : 'Practice mode analyzes your technical depth and generates personalized revision tips.'}
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-100 flex items-center justify-between bg-zinc-50/50">
          {isFinished ? (
            <div className="w-full flex items-center justify-end gap-2">
              <Button
                onClick={() => {
                  onComplete();
                  onClose();
                }}
                className="bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold gap-1.5 px-5 rounded-xl"
              >
                <span>{mode === 'assessment' ? 'Proceed to Next Round' : 'Continue Practice'}</span>
                <ChevronRight className="w-4 h-4 text-lime-400" />
              </Button>
            </div>
          ) : (
            <div className="w-full flex items-center justify-between">
              <span className="text-[11px] text-zinc-400 font-mono">
                {currentQIndex + 1} of {totalQuestions} Questions
              </span>
              <Button
                onClick={() => handleNextQuestion(false)}
                disabled={submitting || loading || !currentAnswer.trim()}
                className="bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold gap-1.5 px-4 rounded-xl"
              >
                <span>{currentQIndex + 1 === totalQuestions ? 'Submit All Explanations' : 'Next Question'}</span>
                <ArrowRight className="w-3.5 h-3.5 text-lime-400" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
