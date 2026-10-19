import React, { useState } from 'react';
import { api } from '../../lib/api';
import { RubricDimension } from '../../lib/types';
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
  const [scores, setScores] = useState<Record<string, number>>({});
  const [reflection, setReflection] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleScoreChange = (dimensionId: string, score: number) => {
    setScores((prev) => ({ ...prev, [dimensionId]: score }));
  };

  const handleSubmit = async () => {
    setError('');

    // Ensure all dimensions are scored
    for (const r of rubrics) {
      if (!scores[r.id]) {
        setError(`Please evaluate your performance on '${r.name}'.`);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      // 1. Submit self-evaluation
      await api.post('/evaluations/self', {
        interview_id: interviewId,
        dimension_scores: scores,
        reflection,
      });

      // 2. Trigger AI evaluation generation
      await api.post(`/evaluations/${interviewId}/generate`);

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

                <div className="grid grid-cols-5 gap-1.5 pt-1">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <button
                      key={s}
                      type="button"
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
