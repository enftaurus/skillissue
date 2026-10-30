import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { RubricDimension, QuestionTurn, QuestionSelfEvaluation } from '../../lib/types';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import { Star, ChevronRight, ChevronLeft, Sparkles } from 'lucide-react';

interface SelfEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  interviewId: string;
  category: string;
  rubrics: RubricDimension[];
  onComplete: () => void;
}

export const SelfEvaluationModal: React.FC<SelfEvaluationModalProps> = ({
  isOpen,
  onClose,
  interviewId,
  rubrics,
  onComplete,
}) => {
  const [activeTab, setActiveTab] = useState<'questions' | 'summary'>('questions');
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [turns, setTurns] = useState<QuestionTurn[]>([]);
  const [questionEvals, setQuestionEvals] = useState<Record<number, { score: number; strengths: string; missed_points: string; confidence: string }>>({});
  const [dimensionScores, setDimensionScores] = useState<Record<string, number>>({});
  const [reflection, setReflection] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && interviewId) {
      try {
        const saved = sessionStorage.getItem(`skillissue_self_eval_${interviewId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.questionEvals) setQuestionEvals(parsed.questionEvals);
          if (parsed.dimensionScores) setDimensionScores(parsed.dimensionScores);
          if (parsed.reflection) setReflection(parsed.reflection);
        }
      } catch {}

      api.get<QuestionTurn[]>(`/interviews/${interviewId}/transcript/grouped`)
        .then((data) => {
          const candidateTurns = data.filter((t) => t.candidate_answer && t.candidate_answer.trim());
          setTurns(candidateTurns);
          // Initialize default score of 3 if not already set
          setQuestionEvals((prev) => {
            const initial = { ...prev };
            candidateTurns.forEach((t) => {
              if (!initial[t.question_index]) {
                initial[t.question_index] = { score: 3, strengths: '', missed_points: '', confidence: 'medium' };
              }
            });
            return initial;
          });
        })
        .catch(() => {});
    }
  }, [isOpen, interviewId]);

  // Persist draft
  useEffect(() => {
    if (interviewId && (Object.keys(questionEvals).length > 0 || reflection)) {
      try {
        sessionStorage.setItem(
          `skillissue_self_eval_${interviewId}`,
          JSON.stringify({ questionEvals, dimensionScores, reflection })
        );
      } catch {}
    }
  }, [interviewId, questionEvals, dimensionScores, reflection]);

  const handleQuestionScore = (idx: number, score: number) => {
    setQuestionEvals((prev) => ({
      ...prev,
      [idx]: {
        ...(prev[idx] || { strengths: '', missed_points: '', confidence: 'medium' }),
        score,
      },
    }));
  };

  const handleQuestionNote = (idx: number, field: 'strengths' | 'missed_points', val: string) => {
    setQuestionEvals((prev) => ({
      ...prev,
      [idx]: {
        ...(prev[idx] || { score: 3, strengths: '', missed_points: '', confidence: 'medium' }),
        [field]: val,
      },
    }));
  };

  const handleSubmit = async () => {
    setError('');
    setIsSubmitting(true);

    try {
      // Auto-compute baseline dimension scores from question scores if not manually set
      const allQScores = Object.values(questionEvals).map((e) => e.score);
      const avgScore = allQScores.length > 0 ? Math.round(allQScores.reduce((a, b) => a + b, 0) / allQScores.length) : 3;

      const finalDimScores: Record<string, number> = { ...dimensionScores };
      for (const r of rubrics) {
        if (!finalDimScores[r.id]) {
          finalDimScores[r.id] = avgScore;
        }
      }

      const formattedQVals: QuestionSelfEvaluation[] = Object.entries(questionEvals).map(([idxStr, val]) => ({
        question_index: parseInt(idxStr),
        score: val.score,
        strengths: val.strengths,
        missed_points: val.missed_points,
        confidence: val.confidence,
      }));

      // 1. Submit per-question self-evaluation
      await api.post('/evaluations/self', {
        interview_id: interviewId,
        dimension_scores: finalDimScores,
        reflection: reflection || 'Candid per-question self-evaluation pass.',
        question_evaluations: formattedQVals,
      });

      // 2. Trigger AI deep evaluation pass
      await api.post(`/evaluations/${interviewId}/generate`);

      try {
        sessionStorage.removeItem(`skillissue_self_eval_${interviewId}`);
      } catch {}

      onComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to submit self-evaluation and generate report.');
      setIsSubmitting(false);
    }
  };

  const currentTurn = turns[currentQIndex];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Candidate Self-Evaluation & Calibration"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-5">
        {/* Banner */}
        <div className="p-4 bg-indigo-50/50 border border-indigo-200/80 rounded-2xl text-xs sm:text-sm text-slate-800 space-y-1.5 shadow-xs">
          <div className="flex items-center gap-2 font-semibold text-indigo-900">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <span>Rate your performance question-by-question</span>
          </div>
          <p className="text-slate-600 leading-relaxed text-xs sm:text-sm">
            Engineers improve by calibrating their self-assessment against objective rubric criteria. Rate how well you answered each question before the AI analysis is unveiled.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
            {error}
          </div>
        )}

        {/* Tab Switcher */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 text-xs sm:text-sm">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('questions')}
              className={`px-3.5 py-1.5 rounded-xl font-medium transition-colors ${
                activeTab === 'questions'
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              1. Question-by-Question Review ({turns.length} turns)
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('summary')}
              className={`px-3.5 py-1.5 rounded-xl font-medium transition-colors ${
                activeTab === 'summary'
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              2. Final Reflection & Submit
            </button>
          </div>
        </div>

        {activeTab === 'questions' && turns.length > 0 && currentTurn ? (
          <div className="space-y-4">
            {/* Question Counter / Navigation Header */}
            <div className="flex items-center justify-between text-xs sm:text-sm font-medium text-slate-500">
              <span>Question {currentQIndex + 1} of {turns.length}</span>
              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={currentQIndex === 0}
                  onClick={() => setCurrentQIndex((prev) => Math.max(0, prev - 1))}
                  className="px-2.5 py-1 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={currentQIndex === turns.length - 1}
                  onClick={() => setCurrentQIndex((prev) => Math.min(turns.length - 1, prev + 1))}
                  className="px-2.5 py-1 text-xs"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>

            {/* Question Turn Card */}
            <div className="p-5 rounded-2xl border border-slate-200/80 bg-slate-50/60 space-y-3.5 text-xs sm:text-sm shadow-xs">
              <div>
                <span className="font-semibold text-slate-400 uppercase tracking-wider text-xs block mb-1">
                  Interviewer Asked:
                </span>
                <p className="font-semibold text-slate-900 text-sm sm:text-base leading-snug">
                  {currentTurn.interviewer_question}
                </p>
              </div>

              <div className="pt-2.5 border-t border-slate-200/60">
                <span className="font-semibold text-slate-400 uppercase tracking-wider text-xs block mb-1">
                  Your Answer:
                </span>
                <p className="italic text-slate-600 bg-white p-3.5 rounded-xl border border-slate-200/80 font-mono text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">
                  &ldquo;{currentTurn.candidate_answer}&rdquo;
                </p>
              </div>
            </div>

            {/* Self-Rating for this Question */}
            <div className="p-5 rounded-2xl border border-slate-200/80 bg-white space-y-3.5 text-xs sm:text-sm shadow-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-900 text-sm">
                  How would you rate your answer to this question?
                </span>
                <span className="font-mono font-bold text-indigo-600 text-base">
                  {questionEvals[currentTurn.question_index]?.score || 3}/5
                </span>
              </div>

              <div className="grid grid-cols-5 gap-2.5">
                {[1, 2, 3, 4, 5].map((score) => {
                  const isSelected = (questionEvals[currentTurn.question_index]?.score || 3) === score;
                  const labels = ['1 (Weak)', '2 (Fair)', '3 (Decent)', '4 (Strong)', '5 (Flawless)'];
                  return (
                    <button
                      key={score}
                      type="button"
                      onClick={() => handleQuestionScore(currentTurn.question_index, score)}
                      className={`py-2.5 px-2 rounded-xl text-xs font-medium border text-center transition-all ${
                        isSelected
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm font-bold'
                          : 'bg-slate-50 text-slate-600 border-slate-200/80 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex justify-center mb-1">
                        <Star className={`w-4 h-4 ${isSelected ? 'fill-white' : ''}`} />
                      </div>
                      <span className="text-xs">{labels[score - 1]}</span>
                    </button>
                  );
                })}
              </div>

              {/* Notes */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
                <div>
                  <label className="text-xs font-semibold text-slate-600 block mb-1">
                    What went well in your answer? (Optional)
                  </label>
                  <input
                    type="text"
                    value={questionEvals[currentTurn.question_index]?.strengths || ''}
                    onChange={(e) => handleQuestionNote(currentTurn.question_index, 'strengths', e.target.value)}
                    placeholder="e.g. Explained indexing trade-offs clearly..."
                    className="w-full px-3.5 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200/80 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600 block mb-1">
                    What did you miss or get stuck on? (Optional)
                  </label>
                  <input
                    type="text"
                    value={questionEvals[currentTurn.question_index]?.missed_points || ''}
                    onChange={(e) => handleQuestionNote(currentTurn.question_index, 'missed_points', e.target.value)}
                    placeholder="e.g. Forgot to mention partition locks..."
                    className="w-full px-3.5 py-2 text-xs sm:text-sm bg-slate-50 border border-slate-200/80 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Stepper Buttons */}
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentQIndex === 0}
                onClick={() => setCurrentQIndex((prev) => prev - 1)}
              >
                Previous Question
              </Button>
              {currentQIndex < turns.length - 1 ? (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setCurrentQIndex((prev) => prev + 1)}
                >
                  Next Question →
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setActiveTab('summary')}
                >
                  Continue to Summary →
                </Button>
              )}
            </div>
          </div>
        ) : (
          /* Summary Tab */
          <div className="space-y-4 text-xs sm:text-sm">
            <div className="p-5 rounded-2xl border border-slate-200/80 bg-white space-y-3 shadow-xs">
              <h4 className="font-semibold text-slate-900 text-sm sm:text-base">Overall Self-Reflection</h4>
              <p className="text-slate-500 text-xs sm:text-sm leading-relaxed">
                Summarize what you learned from this interview and what technical areas you want to prioritize in your personalized improvement plan:
              </p>
              <textarea
                rows={4}
                value={reflection}
                onChange={(e) => setReflection(e.target.value)}
                placeholder="e.g. I felt comfortable with basic API endpoints, but struggled with distributed failure modes, database lock contention, and cache invalidation. Need to focus more on systems internals..."
                className="w-full p-3.5 text-xs sm:text-sm bg-slate-50 border border-slate-200/80 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500"
              />
            </div>

            {/* Review Question Ratings */}
            <div className="p-5 rounded-2xl border border-slate-200/80 bg-slate-50 space-y-2.5 shadow-xs">
              <span className="font-semibold text-slate-400 uppercase tracking-wider text-xs block">
                Question Ratings Summary:
              </span>
              <div className="space-y-2">
                {turns.map((t, i) => (
                  <div key={t.question_index} className="flex items-center justify-between p-3 bg-white rounded-xl border border-slate-200/80 text-xs sm:text-sm">
                    <span className="truncate max-w-[400px] text-slate-800">
                      Q{i + 1}: {t.interviewer_question}
                    </span>
                    <span className="font-mono font-bold text-indigo-600 ml-2">
                      {questionEvals[t.question_index]?.score || 3}/5
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Submit Action */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <Button
                variant="secondary"
                size="md"
                onClick={() => setActiveTab('questions')}
              >
                ← Back to Questions
              </Button>
              <Button
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                onClick={handleSubmit}
                className="shadow-sm"
              >
                <Sparkles className="w-4 h-4 mr-1.5" />
                Submit & Unveil AI Analysis
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
