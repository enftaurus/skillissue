import React, { useEffect, useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { api, ApiError } from '../../lib/api';
import { CodingProblem, CodeExecutionResult, CodingLimits, DsaCoachResponse } from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import {
  AlertCircle,
  CheckCircle2,
  Play,
  RotateCcw,
  Send,
  Terminal,
  XCircle,
  HelpCircle,
  Sparkles,
  Bot,
  MessageSquare,
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
  const [executionError, setExecutionError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'problem' | 'results'>('problem');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [limits, setLimits] = useState<CodingLimits | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // AI Coaching Agent state (on-demand Socratic guidance)
  const [isCoachOpen, setIsCoachOpen] = useState<boolean>(false);
  const [coachLevel, setCoachLevel] = useState<number>(1);
  const [coachHistory, setCoachHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string; level?: number; guidingQuestion?: string; focus?: string }>>([]);
  const [coachUserMessage, setCoachUserMessage] = useState<string>('');
  const [isCoachLoading, setIsCoachLoading] = useState<boolean>(false);
  const [coachError, setCoachError] = useState<string>('');

  // Persistent code drafts cache per problem and language
  const draftsRef = useRef<Record<string, string>>({});

  const getDraftKey = (problemId: string, lang: string) => `skillissue_code_draft_${problemId}_${lang}`;

  const loadDraft = (problemId: string, lang: string, defaultCode: string): string => {
    try {
      const saved = localStorage.getItem(getDraftKey(problemId, lang));
      return saved !== null ? saved : defaultCode;
    } catch {
      return defaultCode;
    }
  };

  const saveDraft = (problemId: string, lang: string, val: string) => {
    try {
      localStorage.setItem(getDraftKey(problemId, lang), val);
    } catch {}
  };

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
      saveDraft(selectedProblem.id, language, code);
    }
    setSelectedProblem(problem);
    setLanguage(lang);
    const starter = problem.starter_code[lang] || '';
    const draft = loadDraft(problem.id, lang, starter);
    draftsRef.current[`${problem.id}_${lang}`] = draft;
    setCode(draft);
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setExecutionError('');
    setActiveTab('problem');

    // Reset coaching conversation for new problem
    setCoachLevel(1);
    setCoachHistory([]);
    setCoachUserMessage('');
    setCoachError('');
    setIsCoachOpen(false);
  };

  const handleRequestCoachHint = async (levelToRequest?: number) => {
    if (!selectedProblem) return;
    const targetLevel = levelToRequest || coachLevel;
    setIsCoachLoading(true);
    setCoachError('');

    try {
      const conversationHistory = coachHistory.map((h) => ({
        role: h.role,
        content: h.content,
      }));

      const res = await api.post<DsaCoachResponse>(`/coding/problems/${selectedProblem.id}/coach`, {
        hint_level: targetLevel,
        user_code: code,
        language,
        user_message: coachUserMessage.trim() || undefined,
        conversation_history: conversationHistory,
      });

      const updatedHistory = [...coachHistory];
      if (coachUserMessage.trim()) {
        updatedHistory.push({
          role: 'user',
          content: coachUserMessage.trim(),
        });
      }
      updatedHistory.push({
        role: 'assistant',
        content: res.hint_text,
        level: res.hint_level,
        guidingQuestion: res.guiding_question,
        focus: res.suggested_focus,
      });

      setCoachHistory(updatedHistory);
      setCoachUserMessage('');
      setCoachLevel(Math.min(4, res.hint_level + 1));
    } catch (err: any) {
      setCoachError(err.message || 'Failed to connect with coaching agent. Please verify AWS Bedrock credentials.');
    } finally {
      setIsCoachLoading(false);
    }
  };

  const handleLanguageChange = (lang: 'python' | 'java' | 'cpp') => {
    if (selectedProblem) {
      draftsRef.current[`${selectedProblem.id}_${language}`] = code;
      saveDraft(selectedProblem.id, language, code);
      const starter = selectedProblem.starter_code[lang] || '';
      const draft = loadDraft(selectedProblem.id, lang, starter);
      draftsRef.current[`${selectedProblem.id}_${lang}`] = draft;
      setCode(draft);
    }
    setLanguage(lang);
  };

  const handleResetCode = () => {
    if (selectedProblem) {
      const starter = selectedProblem.starter_code[language] || '';
      draftsRef.current[`${selectedProblem.id}_${language}`] = starter;
      saveDraft(selectedProblem.id, language, starter);
      setCode(starter);
    }
  };

  const handleRunSampleTests = async () => {
    if (!selectedProblem) return;
    setIsRunning(true);
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setExecutionError('');
    setActiveTab('results');

    try {
      const res = await api.post<CodeExecutionResult>('/coding/run', {
        problem_id: selectedProblem.id,
        language,
        code,
      });
      setExecutionResult(res);
      setExecutionError('');
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : (err?.message || 'Code execution failed. Please check your syntax or limits.');
      setExecutionError(msg);
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmitSolution = async () => {
    if (!selectedProblem) return;
    setIsSubmitting(true);
    setExecutionResult(null);
    setExecutionError('');
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
      setExecutionError('');
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : (err?.message || 'Submission failed.');
      setExecutionError(msg);
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

                  {executionError && (
                    <div className="p-3 mb-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-center justify-between shadow-xs">
                      <span>{executionError}</span>
                      <button
                        onClick={() => setExecutionError('')}
                        className="text-amber-700 hover:text-amber-900 text-xs font-semibold"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}

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
                {selectedProblem?.ai_coaching_supported !== false && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsCoachOpen(true)}
                    className="gap-1.5 text-xs text-lime-900 border-lime-300 bg-lime-50/60 hover:bg-lime-100"
                    title="Request on-demand pedagogical hint from senior mentor"
                  >
                    <HelpCircle className="w-3.5 h-3.5 text-lime-700" />
                    <span>Need Help?</span>
                    {coachHistory.length > 0 && (
                      <span className="w-4 h-4 rounded-full bg-lime-200 text-lime-900 text-[10px] font-bold flex items-center justify-center">
                        {coachHistory.length}
                      </span>
                    )}
                  </Button>
                )}

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
                    saveDraft(selectedProblem.id, language, updated);
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

      {/* Socratic DSA Coaching Modal */}
      <Modal
        isOpen={isCoachOpen}
        onClose={() => setIsCoachOpen(false)}
        title="DSA Coaching Agent (Socratic Mentor)"
      >
        <div className="space-y-4 text-xs">
          {/* Header explanation & level indicator */}
          <div className="p-3 bg-surface-warm rounded-lg border border-surface-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-ink flex items-center gap-1.5">
                <Bot className="w-4 h-4 text-lime-700" />
                <span>Pedagogical Guidance Progression</span>
              </span>
              <Badge variant="lime" size="sm" className="font-mono">
                Hint Level: {coachLevel}/4
              </Badge>
            </div>
            <div className="grid grid-cols-4 gap-1 text-[10px] font-mono">
              {[
                { lvl: 1, label: '1. Nudge' },
                { lvl: 2, label: '2. Pattern' },
                { lvl: 3, label: '3. Derivation' },
                { lvl: 4, label: '4. Pseudocode' },
              ].map((step) => (
                <div
                  key={step.lvl}
                  className={`p-1.5 text-center rounded border transition-colors ${
                    coachLevel >= step.lvl
                      ? 'bg-lime-100 border-lime-300 text-lime-900 font-semibold'
                      : 'bg-white border-surface-border text-ink-faint'
                  }`}
                >
                  {step.label}
                </div>
              ))}
            </div>
            <p className="text-[11px] text-ink-subtle">
              The coach inspects your code and nudges your intuition. It will never provide complete copy-paste solutions.
            </p>
          </div>

          {coachError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded-md flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{coachError}</span>
            </div>
          )}

          {/* Conversation / Hint History */}
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {coachHistory.length === 0 ? (
              <div className="p-6 text-center text-ink-muted border border-dashed border-surface-border rounded-lg space-y-2">
                <MessageSquare className="w-6 h-6 text-ink-subtle mx-auto" />
                <p>No hints requested yet for this problem.</p>
                <p className="text-[11px] text-ink-faint">
                  Stuck on the data structure, Big-O complexity, or tricky edge case? Ask a question or request Level 1 guidance below.
                </p>
              </div>
            ) : (
              coachHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border ${
                    msg.role === 'user'
                      ? 'bg-surface-subtle border-surface-border text-ink'
                      : 'bg-lime-50/40 border-lime-200 text-ink'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-semibold mb-1">
                    <span className={msg.role === 'user' ? 'text-ink-muted' : 'text-lime-800'}>
                      {msg.role === 'user' ? 'Your Question' : `Mentor Hint (Level ${msg.level || idx + 1})`}
                    </span>
                    {msg.focus && (
                      <Badge variant="zinc" size="sm">
                        Focus: {msg.focus}
                      </Badge>
                    )}
                  </div>

                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                  {msg.guidingQuestion && (
                    <div className="mt-2 pt-2 border-t border-lime-200/60 text-lime-900 font-medium flex items-start gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-lime-700 shrink-0 mt-0.5" />
                      <span>{msg.guidingQuestion}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Hint Request Controls */}
          <div className="space-y-2.5 pt-2 border-t border-surface-border">
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
              Ask a question or describe what you've tried (Optional)
            </label>
            <textarea
              rows={2}
              value={coachUserMessage}
              onChange={(e) => setCoachUserMessage(e.target.value)}
              placeholder="e.g. I am thinking of using two pointers, but the array is unsorted. How do I optimize lookup?"
              className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-1 focus:ring-lime-500"
            />

            <div className="flex items-center justify-between gap-3 pt-1">
              <span className="text-[11px] text-ink-subtle">
                {coachLevel > 4 ? 'Max level reached' : `Next up: Level ${coachLevel} guidance`}
              </span>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsCoachOpen(false)}
                >
                  Close
                </Button>

                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={() => handleRequestCoachHint(coachLevel)}
                  isLoading={isCoachLoading}
                  className="flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>
                    {coachHistory.length === 0
                      ? 'Request Level 1 Hint'
                      : coachUserMessage.trim()
                      ? 'Ask Mentor'
                      : `Request Level ${coachLevel} Hint`}
                  </span>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};
