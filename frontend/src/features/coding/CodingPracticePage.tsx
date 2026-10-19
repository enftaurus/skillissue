import React, { useEffect, useState } from 'react';
import { api, ApiError } from '../../lib/api';
import { CodingProblem, CodeExecutionResult } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  AlertCircle,
  CheckCircle2,
  Play,
  RotateCcw,
  Send,
  Terminal,
  XCircle,
} from 'lucide-react';

export const CodingPracticePage: React.FC = () => {
  const [problems, setProblems] = useState<CodingProblem[]>([]);
  const [selectedProblem, setSelectedProblem] = useState<CodingProblem | null>(null);
  const [language, setLanguage] = useState<'python' | 'java' | 'cpp'>('python');
  const [code, setCode] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [executionResult, setExecutionResult] = useState<CodeExecutionResult | null>(null);
  const [submissionSuccess, setSubmissionSuccess] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'description' | 'results'>('description');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const list = await api.get<CodingProblem[]>('/coding/problems');
        setProblems(list);
        if (list.length > 0) {
          selectProblem(list[0], 'python');
        }
      } catch (e) {
        console.error('Failed to load coding problems', e);
      } finally {
        setLoading(false);
      }
    };

    fetchProblems();
  }, []);

  const selectProblem = (problem: CodingProblem, lang: 'python' | 'java' | 'cpp') => {
    setSelectedProblem(problem);
    setLanguage(lang);
    setCode(problem.starter_code[lang] || '');
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setActiveTab('description');
  };

  const handleLanguageChange = (lang: 'python' | 'java' | 'cpp') => {
    setLanguage(lang);
    if (selectedProblem) {
      setCode(selectedProblem.starter_code[lang] || '');
    }
  };

  const handleResetCode = () => {
    if (selectedProblem) {
      setCode(selectedProblem.starter_code[language] || '');
    }
  };

  const handleRunSampleTests = async () => {
    if (!selectedProblem) return;
    setIsRunning(true);
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setActiveTab('results');

    try {
      const res = await api.post<CodeExecutionResult>('/coding/run', {
        problem_id: selectedProblem.id,
        language,
        code,
      });
      setExecutionResult(res);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
      } else {
        alert('Code execution failed.');
      }
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmitSolution = async () => {
    if (!selectedProblem) return;
    setIsSubmitting(true);
    setExecutionResult(null);
    setActiveTab('results');

    try {
      const res = await api.post<any>('/coding/submit', {
        problem_id: selectedProblem.id,
        language,
        code,
      });
      setExecutionResult({
        status: res.status,
        stdout: '',
        stderr: '',
        execution_time_ms: res.execution_time_ms,
        total_passed: res.tests_passed,
        total_tests: res.tests_total,
        test_results: [],
      });
      if (res.status === 'passed') {
        setSubmissionSuccess(true);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.message);
      } else {
        alert('Submission failed.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <div className="w-10 h-10 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-ink-muted">Loading coding sandbox catalog...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 flex items-center justify-center">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-ink">Isolated Coding Sandbox</h1>
            <p className="text-xs text-ink-muted">
              Python 3.12, OpenJDK 21, GCC 13. Resource limits: 128MB RAM, 3.0s CPU timeout, no network.
            </p>
          </div>
        </div>

        {/* Problem Selector Dropdown */}
        <div className="flex items-center gap-3">
          <label className="text-xs text-ink-subtle font-medium">Problem:</label>
          <select
            value={selectedProblem?.id || ''}
            onChange={(e) => {
              const p = problems.find((item) => item.id === e.target.value);
              if (p) selectProblem(p, language);
            }}
            className="text-xs font-medium bg-white border border-surface-border rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-lime-500"
          >
            {problems.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} ({p.difficulty})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Split Layout: Description & Code Editor */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 cols): Problem Description & Specs */}
        <Card className="lg:col-span-5 p-6 bg-white border border-surface-border space-y-5 max-h-[780px] overflow-y-auto">
          {selectedProblem ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-ink">{selectedProblem.title}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge
                      variant={
                        selectedProblem.difficulty === 'easy'
                          ? 'emerald'
                          : selectedProblem.difficulty === 'medium'
                          ? 'lime'
                          : 'zinc'
                      }
                      className="text-[10px] uppercase font-mono"
                    >
                      {selectedProblem.difficulty}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="space-y-4 text-xs text-ink leading-relaxed">
                <div>
                  <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1">
                    Description
                  </h4>
                  <p className="whitespace-pre-line text-ink">{selectedProblem.description}</p>
                </div>

                <div>
                  <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1">
                    Input Format
                  </h4>
                  <p className="font-mono bg-surface-subtle p-2 rounded border border-surface-border text-ink-muted">
                    {selectedProblem.input_format}
                  </p>
                </div>

                <div>
                  <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1">
                    Output Format
                  </h4>
                  <p className="font-mono bg-surface-subtle p-2 rounded border border-surface-border text-ink-muted">
                    {selectedProblem.output_format}
                  </p>
                </div>

                {selectedProblem.constraints && selectedProblem.constraints.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1">
                      Constraints
                    </h4>
                    <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-ink-muted">
                      {selectedProblem.constraints.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div>
                  <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1">
                    Sample Test Cases
                  </h4>
                  <div className="space-y-2">
                    {selectedProblem.sample_test_cases.map((tc, i) => (
                      <div key={i} className="p-2.5 rounded bg-surface-subtle border border-surface-border font-mono text-[11px] space-y-1">
                        <div>
                          <span className="text-ink-subtle">Input:</span> {tc.stdin.trim()}
                        </div>
                        <div>
                          <span className="text-ink-subtle">Expected:</span> {tc.expected_stdout.trim()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <p className="text-xs text-ink-muted">Select a problem to begin.</p>
          )}
        </Card>

        {/* Right Column (7 cols): Language Selection, Code Editor & Results */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="p-4 bg-white border border-surface-border space-y-3">
            {/* Editor Controls Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-surface-border">
              <div className="flex items-center gap-1.5">
                {(['python', 'java', 'cpp'] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => handleLanguageChange(lang)}
                    className={`px-3 py-1 rounded text-xs font-mono font-medium transition-colors ${
                      language === lang
                        ? 'bg-lime-100 text-lime-900 border border-lime-300'
                        : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                    }`}
                  >
                    {lang === 'python' ? 'Python 3' : lang === 'java' ? 'Java 21' : 'C++ 17'}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetCode}
                  title="Reset to starter code"
                  className="text-xs gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleRunSampleTests}
                  isLoading={isRunning}
                  disabled={isSubmitting}
                  className="gap-1.5 text-xs font-medium"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Run Tests
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSubmitSolution}
                  isLoading={isSubmitting}
                  disabled={isRunning}
                  className="gap-1.5 text-xs font-semibold"
                >
                  <Send className="w-3.5 h-3.5" />
                  Submit Solution
                </Button>
              </div>
            </div>

            {/* Code Editor Area */}
            <div className="relative">
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                rows={18}
                spellCheck={false}
                className="w-full font-mono text-xs p-4 bg-zinc-950 text-lime-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-lime-500 leading-relaxed resize-y border border-zinc-800"
                placeholder="// Write your solution here..."
              />
            </div>
          </Card>

          {/* Execution Results View */}
          {activeTab === 'results' && (
            <Card className="p-5 bg-white border border-surface-border space-y-4">
              <div className="flex items-center justify-between border-b border-surface-border pb-3">
                <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-lime-600" />
                  Execution Output
                </h3>

                {executionResult && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-ink-subtle font-mono">
                      {executionResult.execution_time_ms}ms
                    </span>
                    <Badge
                      variant={
                        executionResult.status === 'passed'
                          ? 'emerald'
                          : executionResult.status === 'failed'
                          ? 'rose'
                          : 'zinc'
                      }
                      className="uppercase font-mono text-[10px]"
                    >
                      {executionResult.status}
                    </Badge>
                  </div>
                )}
              </div>

              {isRunning || isSubmitting ? (
                <div className="py-8 text-center">
                  <div className="w-6 h-6 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-xs text-ink-muted">
                    {isRunning ? 'Running sample test cases...' : 'Testing against complete test suite...'}
                  </p>
                </div>
              ) : executionResult ? (
                <div className="space-y-4">
                  {/* Summary status banner */}
                  {submissionSuccess ? (
                    <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>
                        <strong>Accepted!</strong> All {executionResult.total_tests} test cases passed
                        within memory and time limits. Solution saved.
                      </span>
                    </div>
                  ) : executionResult.status === 'failed' ? (
                    <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-xs flex items-center gap-2">
                      <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                      <span>
                        <strong>Wrong Answer:</strong> Passed {executionResult.total_passed} of{' '}
                        {executionResult.total_tests} test cases.
                      </span>
                    </div>
                  ) : executionResult.status === 'compile_error' ? (
                    <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-xs space-y-1">
                      <div className="font-semibold flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4" /> Compilation Error
                      </div>
                      <pre className="font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
                        {executionResult.stderr}
                      </pre>
                    </div>
                  ) : null}

                  {/* Individual test case breakdown if available */}
                  {executionResult.test_results && executionResult.test_results.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
                        Test Cases ({executionResult.total_passed}/{executionResult.total_tests} passed)
                      </h4>
                      {executionResult.test_results.map((tc) => (
                        <div
                          key={tc.test_index}
                          className={`p-3 rounded-lg border text-xs font-mono space-y-1 ${
                            tc.passed
                              ? 'bg-emerald-50/50 border-emerald-200'
                              : 'bg-rose-50/50 border-rose-200'
                          }`}
                        >
                          <div className="flex items-center justify-between font-sans">
                            <span className="font-semibold">
                              Test #{tc.test_index + 1}
                            </span>
                            <span
                              className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                                tc.passed
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              {tc.passed ? 'PASS' : 'FAIL'} ({tc.execution_time_ms}ms)
                            </span>
                          </div>

                          <div className="pt-1 space-y-0.5 text-[11px]">
                            <div>
                              <span className="text-ink-subtle">Input:</span> {tc.stdin.trim()}
                            </div>
                            <div>
                              <span className="text-ink-subtle">Expected:</span>{' '}
                              {tc.expected_stdout.trim()}
                            </div>
                            {!tc.passed && (
                              <div className="text-rose-700 font-bold">
                                <span className="text-rose-900 font-normal">Actual:</span>{' '}
                                {tc.actual_stdout.trim() || '<empty>'}
                              </div>
                            )}
                            {tc.stderr && (
                              <div className="text-rose-600 text-[10px] whitespace-pre-wrap">
                                {tc.stderr}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
