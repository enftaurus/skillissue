import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { RubricDimension, QuestionTurn, QuestionSelfEvaluation } from '../../lib/types';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';

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
  const [activeTab, setActiveTab] = useState<'dimensions' | 'questions'>('dimensions');
  const [scores, setScores] = useState<Record<string, number>>({});
  const [reflection, setReflection] = useState('');
  const [turns, setTurns] = useState<QuestionTurn[]>([]);
  const [questionEvals, setQuestionEvals] = useState<Record<number, { score: number; strengths: string; missed_points: string; confidence: string }>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen && interviewId) {
      try {
        const saved = sessionStorage.getItem(`skillissue_self_eval_${interviewId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.scores) setScores(parsed.scores);
          if (parsed.reflection) setReflection(parsed.reflection);
          if (parsed.questionEvals) setQuestionEvals(parsed.questionEvals);
        }
      } catch {}

      api.get<QuestionTurn[]>(`/interviews/${interviewId}/transcript/grouped`)
        .then((data) => {
          setTurns(data.filter((t) => t.candidate_answer));
        })
        .catch(() => {});
    }
  }, [isOpen, interviewId]);

  // Persist unsaved draft so reopening modal restores entries
  useEffect(() => {
    if (interviewId && (Object.keys(scores).length > 0 || reflection || Object.keys(questionEvals).length > 0)) {
      try {
        sessionStorage.setItem(
          `skillissue_self_eval_${interviewId}`,
          JSON.stringify({ scores, reflection, questionEvals })
        );
      } catch {}
    }
  }, [interviewId, scores, reflection, questionEvals]);

  const handleScoreChange = (dimensionId: string, score: number) => {
    setScores((prev) => ({ ...prev, [dimensionId]: score }));
  };

  const handleQuestionScore = (idx: number, score: number) => {
    setQuestionEvals((prev) => ({
      ...prev,
      [idx]: {
        ...(prev[idx] || { strengths: '', missed_points: '', confidence: 'medium' }),
        score,
      },
    }));
  };

  const handleQuestionNote = (idx: number, field: 'strengths' | 'missed_points' | 'confidence', value: string) => {
    setQuestionEvals((prev) => ({
      ...prev,
      [idx]: {
        ...(prev[idx] || { score: 3, strengths: '', missed_points: '', confidence: 'medium' }),
        [field]: value,
      },
    }));
  };

  const handleSubmit = async () => {
    setError('');

    // Ensure all dimensions are scored
    for (const r of rubrics) {
      if (!scores[r.id]) {
        setError(`Please evaluate your performance on '${r.name}'.`);
        setActiveTab('dimensions');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      // Build question evaluations array
      const formattedQVals: QuestionSelfEvaluation[] = Object.entries(questionEvals).map(([idxStr, val]) => ({
        question_index: parseInt(idxStr),
        score: val.score,
        strengths: val.strengths,
        missed_points: val.missed_points,
        confidence: val.confidence,
      }));

      // 1. Submit self-evaluation
      await api.post('/evaluations/self', {
        interview_id: interviewId,
        dimension_scores: scores,
        reflection,
        question_evaluations: formattedQVals,
      });

      // 2. Trigger AI evaluation generation
      await api.post(`/evaluations/${interviewId}/generate`);

      try {
        sessionStorage.removeItem(`skillissue_self_eval_${interviewId}`);
      } catch {}

      onComplete();
    } catch (err: any) {
      setError(err.message || 'Failed to complete evaluation pass.');
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Candidate Self-Evaluation"
      maxWidth="max-w-2xl"
    >
      <div className="space-y-6">
        <div className="p-3 bg-surface-warm border border-surface-border rounded-lg text-xs text-ink-muted">
          <p className="font-semibold text-ink mb-0.5">Evaluate before revealing AI feedback</p>
          Calibrating self-perception against external benchmarks is how engineers detect blindspots. Be candid about what you nailed and where you struggled.
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-md">
            {error}
          </div>
        )}

        {/* Mode Switcher */}
        <div className="flex border-b border-surface-border text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveTab('dimensions')}
            className={`pb-2.5 px-3 border-b-2 transition-colors ${
              activeTab === 'dimensions'
                ? 'border-lime-600 text-lime-700'
                : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            1. Rubric Dimensions (Required)
          </button>
          {turns.length > 0 && (
            <button
              type="button"
              onClick={() => setActiveTab('questions')}
              className={`pb-2.5 px-3 border-b-2 transition-colors ${
                activeTab === 'questions'
                  ? 'border-lime-600 text-lime-700'
                  : 'border-transparent text-ink-muted hover:text-ink'
              }`}
            >
              2. Per-Question Self-Check ({turns.length} turns)
            </button>
          )}
        </div>

        {activeTab === 'dimensions' ? (
          <div className="space-y-5">
            {rubrics.map((r) => {
              const currentScore = scores[r.id] || 0;
              return (
                <div key={r.id} className="p-4 rounded-lg border border-surface-border bg-white space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-semibold text-sm text-ink">{r.name}</h4>
                      <p className="text-xs text-ink-subtle mt-0.5">{r.description}</p>
                    </div>
                    <span className="text-sm font-bold text-lime-700 shrink-0 ml-3">
                      {currentScore ? `${currentScore}/5` : '—'}
                    </span>
                  </div>

                  <div className="grid grid-cols-5 gap-1.5 pt-1" role="radiogroup" aria-label={`Score for ${r.name}`}>
                    {[1, 2, 3, 4, 5].map((s) => (
                      <button
                        key={s}
                        type="button"
                        role="radio"
                        aria-checked={currentScore === s}
                        aria-label={`${s} out of 5 for ${r.name}`}
                        onClick={() => handleScoreChange(r.id, s)}
                        className={`py-2 text-xs font-semibold rounded border transition-colors ${
                          currentScore === s
                            ? 'bg-lime-600 text-white border-lime-600 shadow-sm'
                            : 'bg-surface-subtle text-ink-muted border-surface-border hover:bg-surface-muted'
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                  {currentScore > 0 && r.scoring_criteria[currentScore] && (
                    <p className="text-[11px] text-ink-muted italic pt-1">
                      "{r.scoring_criteria[currentScore]}"
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="space-y-4 max-h-[420px] overflow-y-auto pr-1">
            {turns.map((turn) => {
              const qEval = questionEvals[turn.question_index] || { score: 0, strengths: '', missed_points: '', confidence: 'medium' };
              return (
                <div key={turn.question_index} className="p-4 rounded-lg border border-surface-border bg-white space-y-3">
                  <div className="flex items-start gap-2.5">
                    <span className="shrink-0 w-5 h-5 rounded-full bg-lime-100 text-lime-800 text-[11px] font-mono font-bold flex items-center justify-center">
                      {turn.question_index}
                    </span>
                    <div className="text-xs">
                      <p className="font-semibold text-ink">{turn.interviewer_question}</p>
                      <p className="text-ink-muted italic mt-1 line-clamp-2 bg-surface-subtle p-2 rounded border border-surface-border">
                        &ldquo;{turn.candidate_answer}&rdquo;
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-surface-border">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-ink-muted uppercase">Your Answer Rating</span>
                      <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <button
                            key={s}
                            type="button"
                            onClick={() => handleQuestionScore(turn.question_index, s)}
                            className={`w-7 h-7 text-xs font-bold rounded border ${
                              qEval.score === s
                                ? 'bg-lime-600 text-white border-lime-600'
                                : 'bg-surface-subtle text-ink-muted border-surface-border hover:bg-surface-muted'
                            }`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div>
                        <label className="block text-[11px] font-medium text-ink-muted mb-0.5">What went well</label>
                        <input
                          type="text"
                          value={qEval.strengths}
                          onChange={(e) => handleQuestionNote(turn.question_index, 'strengths', e.target.value)}
                          placeholder="Key point nailed..."
                          className="w-full px-2.5 py-1.5 text-xs bg-white border border-surface-border rounded text-ink"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-ink-muted mb-0.5">What was missed</label>
                        <input
                          type="text"
                          value={qEval.missed_points}
                          onChange={(e) => handleQuestionNote(turn.question_index, 'missed_points', e.target.value)}
                          placeholder="Caveats or bottlenecks missed..."
                          className="w-full px-2.5 py-1.5 text-xs bg-white border border-surface-border rounded text-ink"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
            Personal Reflection (Optional)
          </label>
          <textarea
            rows={3}
            value={reflection}
            onChange={(e) => setReflection(e.target.value)}
            placeholder="What was your biggest miss or strongest moment in this round?"
            className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-2 focus:ring-lime-500"
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-surface-border">
          <Button variant="ghost" size="md" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={handleSubmit}
            isLoading={isSubmitting}
          >
            Submit & Generate AI Evaluation
          </Button>
        </div>
      </div>
    </Modal>
  );
};
