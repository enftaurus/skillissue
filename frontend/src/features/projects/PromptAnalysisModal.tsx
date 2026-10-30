import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ArrowRight,
  Sparkles,
  RotateCcw,
  BookOpen,
  X,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export interface PromptEvaluationItem {
  prompt_index: number;
  user_prompt: string;
  critique: string;
  improvement_tip: string;
  better_rewrite: string;
  is_amateurish: boolean;
  score: number;
}

export interface PromptAnalysisData {
  overall_score: number;
  grade: string;
  rubric_breakdown: {
    context_specification?: number;
    error_diagnostic_inclusion?: number;
    problem_decomposition?: number;
    engineering_autonomy?: number;
    [key: string]: number | undefined;
  };
  summary: string;
  evaluated_prompts: PromptEvaluationItem[];
  key_takeaways: string[];
}

interface PromptAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: PromptAnalysisData | null;
  testsPassed: number;
  totalTests: number;
  timeSpentSeconds: number;
  onRestart?: () => void;
}

export const PromptAnalysisModal: React.FC<PromptAnalysisModalProps> = ({
  isOpen,
  onClose,
  data,
  testsPassed,
  totalTests,
  timeSpentSeconds,
  onRestart,
}) => {
  if (!isOpen || !data) return null;

  const minutes = Math.floor(timeSpentSeconds / 60);
  const seconds = timeSpentSeconds % 60;
  const timeFormatted = `${minutes}m ${seconds.toString().padStart(2, '0')}s`;

  const amateurCount = data.evaluated_prompts.filter((p) => p.is_amateurish).length;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-4xl w-full border border-slate-200/80 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-200/60 flex items-center justify-center text-indigo-600">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Project Evaluation & Prompt Quality Report</h2>
              <p className="text-xs text-slate-500">
                CI/CD Test Harness Verification & AI Pair-Programming Efficiency Analysis
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Top Score Banner */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Prompt Score</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-extrabold text-indigo-600">{data.overall_score}</span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <span className="text-xs font-medium text-slate-700 mt-1">{data.grade}</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">CI/CD Tests</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span
                  className={`text-3xl font-extrabold ${
                    testsPassed === totalTests ? 'text-emerald-600' : 'text-amber-600'
                  }`}
                >
                  {testsPassed}/{totalTests}
                </span>
                <span className="text-xs text-slate-400">Passed</span>
              </div>
              <span className="text-xs font-medium text-slate-700 mt-1">
                {testsPassed === totalTests ? 'All Assertions Satisfied' : 'Some Tests Failed'}
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Time Invested</span>
              <div className="text-3xl font-extrabold text-slate-900 mt-2 font-mono">{timeFormatted}</div>
              <span className="text-xs font-medium text-slate-700 mt-1">25-min session</span>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Amateur Flags</span>
              <div className="flex items-baseline gap-2 mt-2">
                <span
                  className={`text-3xl font-extrabold ${
                    amateurCount > 0 ? 'text-rose-600' : 'text-emerald-600'
                  }`}
                >
                  {amateurCount}
                </span>
                <span className="text-xs text-slate-400">detected</span>
              </div>
              <span className="text-xs font-medium text-slate-700 mt-1">
                {amateurCount > 0 ? 'Vague / Blanket queries' : 'Clean technical queries'}
              </span>
            </div>
          </div>

          {/* Executive Summary */}
          <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 space-y-2">
            <div className="flex items-center gap-2 text-indigo-900 font-semibold text-sm">
              <BookOpen className="w-4 h-4 text-indigo-600" />
              <span>Evaluator Synthesis</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">{data.summary}</p>
          </div>

          {/* Rubric Breakdown Grid */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Prompt Engineering Rubric Breakdown (out of 25)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-white border border-slate-200/80">
                <div className="text-[11px] text-slate-500 font-medium">Context & Files</div>
                <div className="text-lg font-bold text-slate-900 mt-1">
                  {data.rubric_breakdown.context_specification ?? 18}
                  <span className="text-xs text-slate-400 font-normal"> / 25</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-white border border-slate-200/80">
                <div className="text-[11px] text-slate-500 font-medium">Error Diagnostics</div>
                <div className="text-lg font-bold text-slate-900 mt-1">
                  {data.rubric_breakdown.error_diagnostic_inclusion ?? 16}
                  <span className="text-xs text-slate-400 font-normal"> / 25</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-white border border-slate-200/80">
                <div className="text-[11px] text-slate-500 font-medium">Decomposition</div>
                <div className="text-lg font-bold text-slate-900 mt-1">
                  {data.rubric_breakdown.problem_decomposition ?? 20}
                  <span className="text-xs text-slate-400 font-normal"> / 25</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-white border border-slate-200/80">
                <div className="text-[11px] text-slate-500 font-medium">Autonomy & Logic</div>
                <div className="text-lg font-bold text-slate-900 mt-1">
                  {data.rubric_breakdown.engineering_autonomy ?? 17}
                  <span className="text-xs text-slate-400 font-normal"> / 25</span>
                </div>
              </div>
            </div>
          </div>

          {/* Evaluated Prompts Breakdown */}
          {data.evaluated_prompts.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Detailed Prompt Analysis & Senior Rewrites</span>
                <span className="text-slate-400 font-normal">{data.evaluated_prompts.length} Prompts Evaluated</span>
              </h3>

              <div className="space-y-4">
                {data.evaluated_prompts.map((item) => (
                  <div
                    key={item.prompt_index}
                    className={`p-4 rounded-xl border transition-all ${
                      item.is_amateurish
                        ? 'bg-rose-50/30 border-rose-200/80'
                        : 'bg-white border-slate-200/80'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-500">
                          #{item.prompt_index}
                        </span>
                        {item.is_amateurish ? (
                          <Badge variant="rose" size="sm" className="gap-1 font-semibold text-[10px]">
                            <AlertTriangle className="w-3 h-3" />
                            <span>Amateurish Prompt Flagged</span>
                          </Badge>
                        ) : (
                          <Badge variant="emerald" size="sm" className="gap-1 font-semibold text-[10px]">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Effective Technical Prompt</span>
                          </Badge>
                        )}
                      </div>
                      <span className="font-mono text-xs font-bold text-slate-700">
                        Score: {item.score}/100
                      </span>
                    </div>

                    {/* Candidate's original prompt */}
                    <div className="mb-2">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
                        What you asked:
                      </span>
                      <p className="mt-0.5 text-xs sm:text-sm font-mono bg-slate-100/80 px-3 py-1.5 rounded-lg text-slate-900 border border-slate-200/60">
                        &ldquo;{item.user_prompt}&rdquo;
                      </p>
                    </div>

                    {/* Critique */}
                    <p className="text-xs text-slate-600 mb-2 leading-relaxed">
                      <strong>Critique:</strong> {item.critique}
                    </p>

                    {/* Improvement Tip */}
                    <div className="flex items-start gap-1.5 text-xs text-slate-700 mb-3 bg-amber-50/50 border border-amber-200/60 p-2.5 rounded-lg">
                      <Lightbulb className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                      <span>
                        <strong>Improvement Advice:</strong> {item.improvement_tip}
                      </span>
                    </div>

                    {/* Better Senior Rewrite */}
                    <div className="p-3 rounded-lg bg-emerald-50/60 border border-emerald-200/80 space-y-1">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-800 uppercase tracking-wide">
                        <ArrowRight className="w-3.5 h-3.5" />
                        <span>How a Staff / Senior Engineer would ask this:</span>
                      </div>
                      <p className="text-xs font-mono text-emerald-950 whitespace-pre-wrap leading-relaxed">
                        {item.better_rewrite}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Key Takeaways */}
          {data.key_takeaways && data.key_takeaways.length > 0 && (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Key Takeaways for Senior Engineering Interviews
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-600">
                {data.key_takeaways.map((tip, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-indigo-600 font-bold">•</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="text-xs text-slate-500">
            Recorded to profile portfolio • Evaluated with Azure / Bedrock LLM
          </div>
          <div className="flex items-center gap-3">
            {onRestart && (
              <Button variant="ghost" size="sm" onClick={onRestart} className="gap-1.5 text-xs">
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Challenge</span>
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={onClose} className="text-xs font-semibold">
              <span>Close Report</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
