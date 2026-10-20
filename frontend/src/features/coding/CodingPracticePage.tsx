import React, { useEffect, useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { api, ApiError } from '../../lib/api';
import { CodingProblem, CodeExecutionResult, CodingLimits } from '../../lib/types';
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
  const [activeTab, setActiveTab] = useState<'problem' | 'results'>('problem');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [limits, setLimits] = useState<CodingLimits | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Persistent code drafts cache per problem and language
  const draftsRef = useRef<Record<string, string>>({});

  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        const [list, limitsData] = await Promise.all([
          api.get<CodingProblem[]>('/coding/problems'),
          api.get<CodingLimits>('/coding/limits').catch(() => null),
        ]);
        setProblems(list);
        if (limitsData) setLimits(limitsData);
        if (list.length > 0) {
          selectProblem(list[0], 'python');
        }
      } catch (e) {
        console.error('Failed to load coding problems', e);
      } finally {
        setLoading(false);
      }
    };

    fetchCatalog();
  }, []);

  const selectProblem = (problem: CodingProblem, lang: 'python' | 'java' | 'cpp') => {
    if (selectedProblem) {
      draftsRef.current[`${selectedProblem.id}_${language}`] = code;
    }
    setSelectedProblem(problem);
    setLanguage(lang);
    const key = `${problem.id}_${lang}`;
    const draft = draftsRef.current[key];
    setCode(draft !== undefined ? draft : (problem.starter_code[lang] || ''));
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setActiveTab('problem');
  };

  const handleLanguageChange = (lang: 'python' | 'java' | 'cpp') => {
    if (selectedProblem) {
      draftsRef.current[`${selectedProblem.id}_${language}`] = code;
      const nextKey = `${selectedProblem.id}_${lang}`;
      const draft = draftsRef.current[nextKey];
      setCode(draft !== undefined ? draft : (selectedProblem.starter_code[lang] || ''));
    }
    setLanguage(lang);
  };

  const handleResetCode = () => {
    if (selectedProblem) {
      const starter = selectedProblem.starter_code[language] || '';
      draftsRef.current[`${selectedProblem.id}_${language}`] = starter;
      setCode(starter);
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

  const categories = ['all', ...Array.from(new Set(problems.map((p) => (p as any).category).filter(Boolean)))];

  const filteredProblems = problems.filter((p) => {
    if (selectedCategory === 'all') return true;
    return (p as any).category === selectedCategory;
  });

  const monacoLanguage = language === 'cpp' ? 'cpp' : language === 'java' ? 'java' : 'python';

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-ink-muted">Booting sandboxed execution environment...</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-surface-warm overflow-hidden">
      {/* Top Arena Navigation Bar */}
      <div className="h-14 px-4 bg-white border-b border-surface-border flex items-center justify-between gap-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-lime-500/10 border border-lime-500/20 text-lime-700 flex items-center justify-center font-bold text-xs">
            DSA
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-ink">Algorithm Arena</h1>
              <span className="text-ink-subtle">•</span>
              <span className="text-xs font-semibold text-ink-muted">
                {selectedProblem?.title || 'Select a problem'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-[10px] text-ink-subtle">
              <span>Docker Isolated</span>
              <span>•</span>
              <span>{limits ? `${limits.memory_limit_mb}MB RAM · ${limits.timeout_seconds}s CPU` : '256MB RAM · 3.0s CPU'}</span>
              <span>•</span>
              <span>No Host Subprocess Path</span>
            </div>
          </div>
        </div>

        {/* Problem and Category Selector */}
        <div className="flex items-center gap-2">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="text-xs font-medium bg-surface-subtle border border-surface-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-lime-500 text-ink-muted"
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c === 'all' ? 'All Categories' : c.toUpperCase()}
              </option>
            ))}
          </select>

          {/* Problem Selector Dropdown */}
          <select
            value={selectedProblem?.id || ''}
            onChange={(e) => {
              const p = problems.find((item) => item.id === e.target.value);
              if (p) selectProblem(p, language);
            }}
            className="text-xs font-medium bg-white border border-surface-border rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-lime-500 text-ink shadow-sm"
          >
            {filteredProblems.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} ({p.difficulty.toUpperCase()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Resizable Split Workspace */}
      <div className="flex-1 min-h-0">
        <PanelGroup orientation="horizontal" className="h-full">
          {/* Left Panel: Problem Description, Constraints, and Test Cases */}
          <Panel defaultSize={40} minSize={25} className="bg-white flex flex-col h-full border-r border-surface-border">
            {/* Tab header */}
            <div className="h-10 px-4 border-b border-surface-border flex items-center justify-between bg-surface-warm/40">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab('problem')}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    activeTab === 'problem'
                      ? 'bg-white text-ink shadow-sm border border-surface-border'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  Problem Description
                </button>
                <button
                  onClick={() => setActiveTab('results')}
                  className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1.5 transition-colors ${
                    activeTab === 'results'
                      ? 'bg-white text-ink shadow-sm border border-surface-border'
                      : 'text-ink-muted hover:text-ink'
                  }`}
                >
                  <span>Execution Output</span>
                  {executionResult && (
                    <span
                      className={`w-2 h-2 rounded-full ${
                        executionResult.status === 'passed' ? 'bg-emerald-500' : 'bg-rose-500'
                      }`}
                    />
                  )}
                </button>
              </div>

              {selectedProblem && (
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
              )}
            </div>

            {/* Panel Content Body */}
            <div className="flex-1 overflow-y-auto p-5 text-xs text-ink space-y-5">
              {activeTab === 'problem' ? (
                selectedProblem ? (
                  <>
                    <div>
                      <h2 className="text-base font-bold text-ink mb-1.5">{selectedProblem.title}</h2>
                      <p className="whitespace-pre-line text-ink leading-relaxed">{selectedProblem.description}</p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1.5">
                        Input Specification
                      </h4>
                      <p className="font-mono bg-surface-subtle p-2.5 rounded-lg border border-surface-border text-ink-muted">
                        {selectedProblem.input_format}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1.5">
                        Output Specification
                      </h4>
                      <p className="font-mono bg-surface-subtle p-2.5 rounded-lg border border-surface-border text-ink-muted">
                        {selectedProblem.output_format}
                      </p>
                    </div>

                    {selectedProblem.constraints && selectedProblem.constraints.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-1.5">
                          Constraints
                        </h4>
                        <ul className="list-disc list-inside space-y-1 font-mono text-[11px] text-ink-muted bg-surface-warm p-2.5 rounded-lg border border-surface-border">
                          {selectedProblem.constraints.map((c, i) => (
                            <li key={i}>{c}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div>
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px] mb-2">
                        Sample Test Cases
                      </h4>
                      <div className="space-y-2.5">
                        {selectedProblem.sample_test_cases.map((tc, i) => (
                          <div
                            key={i}
                            className="p-3 rounded-lg bg-surface-subtle border border-surface-border font-mono text-[11px] space-y-1"
                          >
                            <div className="text-[10px] uppercase font-semibold text-ink-subtle tracking-wider mb-1">
                              Example {i + 1}
                            </div>
                            <div>
                              <span className="text-ink-subtle">Input:</span> {tc.stdin.trim()}
                            </div>
                            <div>
                              <span className="text-ink-subtle">Output:</span> {tc.expected_stdout.trim()}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <p className="text-ink-muted">Select a problem from the dropdown.</p>
                )
              ) : (
                /* Execution Output View */
                <div className="space-y-4">
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
                    <div className="py-12 text-center">
                      <div className="w-7 h-7 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-xs text-ink-muted font-medium">
                        {isRunning ? 'Running sample test cases...' : 'Executing against complete test suite...'}
                      </p>
                    </div>
                  ) : executionResult ? (
                    <div className="space-y-4">
                      {submissionSuccess ? (
                        <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                          <span>
                            <strong>Accepted!</strong> All {executionResult.total_tests} test cases passed.
                            Skill mastery progression recorded.
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

                      {/* Test case breakdown */}
                      {executionResult.test_results && executionResult.test_results.length > 0 && (
                        <div className="space-y-2">
                          <h4 className="text-xs font-semibold text-ink-subtle uppercase tracking-wider">
                            Sample Test Results ({executionResult.total_passed}/{executionResult.total_tests} passed)
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
                                <span className="font-semibold">Test #{tc.test_index + 1}</span>
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
                                  <span className="text-ink-subtle">Expected:</span> {tc.expected_stdout.trim()}
                                </div>
                                {!tc.passed && (
                                  <div className="text-rose-700 font-bold">
                                    <span className="text-rose-900 font-normal">Actual:</span>{' '}
                                    {tc.actual_stdout.trim() || '<empty>'}
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="py-12 text-center text-ink-muted text-xs">
                      Click <strong>Run Tests</strong> or <strong>Submit Solution</strong> to view execution results.
                    </div>
                  )}
                </div>
              )}
            </div>
          </Panel>

          {/* Resizable Divider Handle */}
          <PanelResizeHandle className="w-1.5 bg-surface-border hover:bg-lime-500 transition-colors cursor-col-resize" />

          {/* Right Panel: Monaco Editor & Controls */}
          <Panel defaultSize={60} minSize={35} className="bg-white flex flex-col h-full">
            {/* Editor Toolbar Header */}
            <div className="h-10 px-4 border-b border-surface-border flex items-center justify-between bg-surface-warm/40 flex-shrink-0">
              <div className="flex items-center gap-1.5">
                {(['python', 'java', 'cpp'] as const).map((lang) => (
                  <button
                    key={lang}
                    onClick={() => handleLanguageChange(lang)}
                    className={`px-3 py-1 rounded text-xs font-mono font-medium transition-colors ${
                      language === lang
                        ? 'bg-lime-100 text-lime-900 border border-lime-300 font-semibold'
                        : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                    }`}
                  >
                    {lang === 'python' ? 'Python 3.12' : lang === 'java' ? 'Java 21' : 'C++ 17'}
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

            {/* Monaco Editor Container */}
            <div className="flex-1 min-h-0 relative">
              <Editor
                height="100%"
                language={monacoLanguage}
                theme="vs"
                value={code}
                onChange={(val) => {
                  const updated = val || '';
                  setCode(updated);
                  if (selectedProblem) {
                    draftsRef.current[`${selectedProblem.id}_${language}`] = updated;
                  }
                }}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  scrollBeyondLastLine: false,
                  lineNumbers: 'on',
                  tabSize: 4,
                  automaticLayout: true,
                  renderLineHighlight: 'all',
                  overviewRulerLanes: 0,
                  hideCursorInOverviewRuler: true,
                }}
              />
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};
