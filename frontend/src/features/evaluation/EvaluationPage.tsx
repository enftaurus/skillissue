import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../../lib/api';
import { Evaluation, EvaluationComparison, Plan } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import {
  AlertTriangle,
  CheckCircle2,
  Flame,
  HelpCircle,
  Quote,
} from 'lucide-react';

export const EvaluationPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;

    Promise.all([
      api.get<Evaluation>(`/evaluations/${id}`),
      api.get<EvaluationComparison>(`/evaluations/${id}/comparison`),
    ])
      .then(([evalData, compData]) => {
        setEvaluation(evalData);
        setComparison(compData);
      })
      .catch((err) => setError(err.message || 'Failed to load evaluation findings.'))
      .finally(() => setLoading(false));
  }, [id]);

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
        <p className="text-sm text-red-600 font-medium">{error || 'Evaluation not found'}</p>
        <Link to="/">
          <Button variant="secondary" size="sm">Return to Dashboard</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
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
            Scores reflect coaching estimates based on observable transcript evidence, not hiring decisions.
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

      {/* Overall Score & Self-Perception Delta */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="sm:col-span-1 bg-surface-warm border-lime-200 flex flex-col justify-between">
          <div>
            <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
              Overall Calibrated Score
            </span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-4xl font-extrabold text-ink font-mono">
                {Math.round(evaluation.overall_score)}
              </span>
              <span className="text-xs text-ink-subtle">/ 100</span>
            </div>
          </div>
          <p className="text-xs text-ink-subtle mt-4">
            Benchmark performance across technical depth, system trade-offs, and communication clarity.
          </p>
        </Card>

        <Card className="sm:col-span-2 space-y-3">
          <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
            Self-Awareness Calibration (Self vs AI Score)
          </span>
          <div className="space-y-2 pt-1">
            {comparison?.dimensions.map((dim) => (
              <div key={dim.dimension_id} className="flex items-center justify-between text-xs py-1 border-b border-surface-border/60 last:border-0">
                <span className="font-medium text-ink">{dim.dimension_name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-ink-subtle font-mono">
                    Self: {dim.self_score ? `${dim.self_score}/5` : '—'}
                  </span>
                  <span className="font-mono font-bold text-ink">
                    AI: {dim.ai_score}/5
                  </span>
                  {dim.delta !== undefined && dim.delta !== null && (
                    <span
                      className={`inline-flex items-center gap-0.5 font-semibold font-mono ${
                        dim.delta > 0
                          ? 'text-lime-700'
                          : dim.delta < 0
                          ? 'text-amber-700'
                          : 'text-ink-subtle'
                      }`}
                    >
                      {dim.delta > 0 && '+'}
                      {dim.delta}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Strengths & Weaknesses Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Strengths */}
        <Card className="border-lime-200 bg-lime-50/20 space-y-3">
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
        <Card className="border-amber-200 bg-amber-50/20 space-y-3">
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
        <Card className="space-y-3">
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

      {/* Rubric Dimensions with Direct Evidence Quotes */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-ink">Rubric Evidence & Quotes</h3>
        <div className="space-y-3">
          {comparison?.dimensions.map((dim) => (
            <Card key={dim.dimension_id} className="space-y-3">
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
                  <span>"{dim.evidence_quote}"</span>
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
