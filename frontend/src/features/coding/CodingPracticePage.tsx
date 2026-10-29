import React, { useEffect, useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { api, ApiError } from '../../lib/api';
import {
  CodingProblem,
  CodeExecutionResult,
  CodingLimits,
  DsaCoachResponse,
  CodingSubmission,
} from '../../lib/types';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock,
  Copy,
  FileText,
  HelpCircle,
  History,
  Lightbulb,
  MessageSquare,
  Play,
  RotateCcw,
  Send,
  Sparkles,
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
  const [executionError, setExecutionError] = useState<string>('');
  const [limits, setLimits] = useState<CodingLimits | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Left panel active tab: 'description' | 'hints' | 'submissions'
  const [leftTab, setLeftTab] = useState<'description' | 'hints' | 'submissions'>('description');

  // Submissions history for this problem
  const [submissions, setSubmissions] = useState<CodingSubmission[]>([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState<boolean>(false);

  // Bottom Console Drawer state
  const [isConsoleOpen, setIsConsoleOpen] = useState<boolean>(true);
  const [consoleTab, setConsoleTab] = useState<'testcase' | 'result'>('testcase');
  const [selectedCaseIndex, setSelectedCaseIndex] = useState<number>(0);
  const [isCustomCase, setIsCustomCase] = useState<boolean>(false);
  const [customStdin, setCustomStdin] = useState<string>('');
  const [copyCodeSuccess, setCopyCodeSuccess] = useState<boolean>(false);

  // AI Coaching Agent state (on-demand Socratic guidance)
  const [coachLevel, setCoachLevel] = useState<number>(1);
  const [coachHistory, setCoachHistory] = useState<
    Array<{
      role: 'user' | 'assistant';
      content: string;
      level?: number;
      guidingQuestion?: string;
      focus?: string;
    }>
  >([]);
  const [coachUserMessage, setCoachUserMessage] = useState<string>('');
  const [isCoachLoading, setIsCoachLoading] = useState<boolean>(false);
  const [coachError, setCoachError] = useState<string>('');

  // Persistent code drafts cache per problem and language
  const draftsRef = useRef<Record<string, string>>({});

  const getDraftKey = (problemId: string, lang: string) =>
    `skillissue_code_draft_${problemId}_${lang}`;

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

  const fetchSubmissions = async () => {
    setLoadingSubmissions(true);
    try {
      const data = await api.get<CodingSubmission[]>('/coding/submissions');
      setSubmissions(data || []);
    } catch (e) {
      console.warn('Failed to fetch submissions', e);
    } finally {
      setLoadingSubmissions(false);
    }
  };

  useEffect(() => {
    if (leftTab === 'submissions') {
      fetchSubmissions();
    }
  }, [leftTab]);

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
    setSelectedCaseIndex(0);
    setIsCustomCase(false);
    setCustomStdin(problem.sample_test_cases[0]?.stdin || '');

    // Reset coaching conversation for new problem
    setCoachLevel(1);
    setCoachHistory([]);
    setCoachUserMessage('');
    setCoachError('');
  };

  const handleNextProblem = () => {
    if (!selectedProblem || problems.length === 0) return;
    const currentIndex = problems.findIndex((p) => p.id === selectedProblem.id);
    const nextIndex = (currentIndex + 1) % problems.length;
    selectProblem(problems[nextIndex], language);
  };

  const handlePrevProblem = () => {
    if (!selectedProblem || problems.length === 0) return;
    const currentIndex = problems.findIndex((p) => p.id === selectedProblem.id);
    const prevIndex = (currentIndex - 1 + problems.length) % problems.length;
    selectProblem(problems[prevIndex], language);
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

  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopyCodeSuccess(true);
    setTimeout(() => setCopyCodeSuccess(false), 2000);
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

      const res = await api.post<DsaCoachResponse>(
        `/coding/problems/${selectedProblem.id}/coach`,
        {
          hint_level: targetLevel,
          user_code: code,
          language,
          user_message: coachUserMessage.trim() || undefined,
          conversation_history: conversationHistory,
        }
      );

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
      setCoachError(
        err.message ||
          'Failed to connect with coaching agent. Please verify LLM provider configuration.'
      );
    } finally {
      setIsCoachLoading(false);
    }
  };

  const handleRunCode = async () => {
    if (!selectedProblem) return;
    setIsRunning(true);
    setExecutionResult(null);
    setSubmissionSuccess(false);
    setExecutionError('');
    setIsConsoleOpen(true);
    setConsoleTab('result');

    try {
      const res = await api.post<CodeExecutionResult>('/coding/run', {
        problem_id: selectedProblem.id,
        language,
        code,
        custom_stdin: isCustomCase ? customStdin : undefined,
      });
      setExecutionResult(res);
      setSelectedCaseIndex(0);
      setExecutionError('');
    } catch (err: any) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err?.message || 'Code execution failed. Please check your syntax or limits.';
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
    setIsConsoleOpen(true);
    setConsoleTab('result');

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
        test_results: res.test_results || [],
      });
      if (res.status === 'passed') {
        setSubmissionSuccess(true);
      }
      setSelectedCaseIndex(0);
      setExecutionError('');
      // Refresh submissions if on submissions tab
      fetchSubmissions();
    } catch (err: any) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err?.message || 'Submission failed. Please check network connectivity.';
      setExecutionError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const monacoLanguage = language === 'cpp' ? 'cpp' : language === 'java' ? 'java' : 'python';

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-ink-muted">Booting sandboxed execution environment...</p>
      </div>
    );
  }

  const problemSubmissions = submissions.filter(
    (s) => s.problem_title === selectedProblem?.title
  );

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col bg-surface-warm overflow-hidden">
      {/* Top LeetCode Navigation Bar */}
      <div className="h-12 px-4 bg-white border-b border-surface-border flex items-center justify-between gap-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          {/* Problem Selector with Prev/Next buttons */}
          <div className="flex items-center gap-1">
            <button
              onClick={handlePrevProblem}
              title="Previous Problem"
              className="p-1 rounded-md text-ink-muted hover:text-ink hover:bg-surface-subtle transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <select
              value={selectedProblem?.id || ''}
              onChange={(e) => {
                const p = problems.find((item) => item.id === e.target.value);
                if (p) selectProblem(p, language);
              }}
              className="text-xs font-semibold bg-surface-subtle border border-surface-border rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-lime-500 text-ink cursor-pointer hover:bg-surface-warm transition-colors"
            >
              {problems.map((p, idx) => (
                <option key={p.id} value={p.id}>
                  {idx + 1}. {p.title}
                </option>
              ))}
            </select>

            <button
              onClick={handleNextProblem}
              title="Next Problem"
              className="p-1 rounded-md text-ink-muted hover:text-ink hover:bg-surface-subtle transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {selectedProblem && (
            <Badge
              variant={
                selectedProblem.difficulty === 'easy'
                  ? 'emerald'
                  : selectedProblem.difficulty === 'medium'
                  ? 'amber'
                  : 'rose'
              }
              size="sm"
              className="capitalize font-mono text-[10px]"
            >
              {selectedProblem.difficulty}
            </Badge>
          )}

          {selectedProblem?.category && (
            <span className="hidden sm:inline-block text-[11px] font-medium text-ink-subtle uppercase px-2 py-0.5 rounded bg-surface-subtle border border-surface-border">
              {selectedProblem.category}
            </span>
          )}
        </div>

        {/* Runtime & Sandbox Status */}
        <div className="flex items-center gap-3 text-xs text-ink-subtle">
          <div className="hidden md:flex items-center gap-1.5 font-mono text-[11px]">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Sandbox: {limits ? `${limits.memory_limit_mb}MB RAM · ${limits.timeout_seconds}s CPU` : '256MB RAM · 3.0s'}</span>
          </div>
        </div>
      </div>

      {/* Main Split Pane: Left Description / Hints / Submissions vs Right Editor & Console */}
      <div className="flex-1 min-h-0">
        <PanelGroup orientation="horizontal" className="h-full">
          {/* LEFT PANEL: LeetCode Style Problem Tabs (45% default) */}
          <Panel defaultSize={45} minSize={30} className="bg-white flex flex-col h-full border-r border-surface-border">
            {/* Header Tabs */}
            <div className="h-10 px-3 border-b border-surface-border flex items-center justify-between bg-surface-warm/50 flex-shrink-0">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setLeftTab('description')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                    leftTab === 'description'
                      ? 'bg-white text-ink shadow-xs border border-surface-border'
                      : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 text-lime-700" />
                  <span>Description</span>
                </button>

                <button
                  onClick={() => setLeftTab('hints')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                    leftTab === 'hints'
                      ? 'bg-white text-ink shadow-xs border border-surface-border'
                      : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                  }`}
                >
                  <Lightbulb className="w-3.5 h-3.5 text-amber-600" />
                  <span>Hints & Coach</span>
                  {coachHistory.length > 0 && (
                    <span className="w-4 h-4 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold flex items-center justify-center">
                      {coachHistory.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setLeftTab('submissions')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors ${
                    leftTab === 'submissions'
                      ? 'bg-white text-ink shadow-xs border border-surface-border'
                      : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                  }`}
                >
                  <History className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Submissions</span>
                  {problemSubmissions.length > 0 && (
                    <span className="w-4 h-4 rounded-full bg-surface-subtle text-ink-muted text-[10px] font-bold flex items-center justify-center border border-surface-border">
                      {problemSubmissions.length}
                    </span>
                  )}
                </button>
              </div>
            </div>

            {/* Left Tab Body */}
            <div className="flex-1 overflow-y-auto p-5 text-xs text-ink space-y-6">
              {/* TAB 1: Problem Description */}
              {leftTab === 'description' && selectedProblem && (
                <div className="space-y-5">
                  <div>
                    <h2 className="text-lg font-bold text-ink mb-1.5">
                      {selectedProblem.title}
                    </h2>
                    <div className="flex items-center gap-2 mb-3">
                      <Badge
                        variant={
                          selectedProblem.difficulty === 'easy'
                            ? 'emerald'
                            : selectedProblem.difficulty === 'medium'
                            ? 'amber'
                            : 'rose'
                        }
                        size="sm"
                        className="capitalize font-mono text-[10px]"
                      >
                        {selectedProblem.difficulty}
                      </Badge>
                      {selectedProblem.category && (
                        <span className="text-[11px] font-mono text-ink-subtle">
                          Topic: {selectedProblem.category}
                        </span>
                      )}
                    </div>
                    <p className="whitespace-pre-line text-ink leading-relaxed text-xs">
                      {selectedProblem.description}
                    </p>
                  </div>

                  {/* LeetCode Example Blocks */}
                  {selectedProblem.sample_test_cases && selectedProblem.sample_test_cases.length > 0 && (
                    <div className="space-y-3.5">
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px]">
                        Examples
                      </h4>
                      {selectedProblem.sample_test_cases.map((tc, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-lg bg-surface-subtle border border-surface-border space-y-2 text-xs"
                        >
                          <div className="font-semibold text-ink text-[11px]">
                            Example {idx + 1}:
                          </div>
                          <div className="font-mono text-[11px] space-y-1 bg-white p-2.5 rounded border border-surface-border/80">
                            <div>
                              <span className="font-semibold text-ink-subtle">Input: </span>
                              <span className="text-ink whitespace-pre-wrap">{tc.stdin.trim()}</span>
                            </div>
                            <div>
                              <span className="font-semibold text-ink-subtle">Output: </span>
                              <span className="text-ink whitespace-pre-wrap">{tc.expected_stdout.trim()}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Constraints */}
                  {selectedProblem.constraints && selectedProblem.constraints.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[11px]">
                        Constraints
                      </h4>
                      <ul className="space-y-1 text-xs">
                        {selectedProblem.constraints.map((c, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-lime-600 font-bold">•</span>
                            <code className="font-mono text-[11px] bg-surface-subtle px-1.5 py-0.5 rounded text-ink border border-surface-border">
                              {c}
                            </code>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Input / Output Formats */}
                  <div className="space-y-3 pt-2 border-t border-surface-border">
                    <div>
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[10px] mb-1">
                        Input Format
                      </h4>
                      <p className="font-mono text-[11px] text-ink-muted bg-surface-warm p-2 rounded border border-surface-border">
                        {selectedProblem.input_format}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-semibold text-ink-subtle uppercase tracking-wider text-[10px] mb-1">
                        Output Format
                      </h4>
                      <p className="font-mono text-[11px] text-ink-muted bg-surface-warm p-2 rounded border border-surface-border">
                        {selectedProblem.output_format}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Hints & Socratic Coach */}
              {leftTab === 'hints' && (
                <div className="space-y-4">
                  <div className="p-3 bg-surface-warm rounded-lg border border-surface-border space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-ink flex items-center gap-1.5 text-xs">
                        <Sparkles className="w-4 h-4 text-lime-700" />
                        <span>Socratic Hint Ladder</span>
                      </span>
                      <Badge variant="lime" size="sm" className="font-mono text-[10px]">
                        Level {coachLevel}/4
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
                      Inspects your current code and nudges your intuition without spoiling the full solution.
                    </p>
                  </div>

                  {coachError && (
                    <div className="p-3 bg-red-50 border border-red-200 text-red-900 rounded-md text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                      <span>{coachError}</span>
                    </div>
                  )}

                  {/* Hint conversation history */}
                  <div className="space-y-3">
                    {coachHistory.length === 0 ? (
                      <div className="p-8 text-center text-ink-muted border border-dashed border-surface-border rounded-lg space-y-2">
                        <MessageSquare className="w-6 h-6 text-ink-subtle mx-auto" />
                        <p className="text-xs">No hints requested yet.</p>
                        <p className="text-[11px] text-ink-faint">
                          Stuck on Big-O, edge cases, or algorithm structure? Request a Level 1 nudge below.
                        </p>
                      </div>
                    ) : (
                      coachHistory.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`p-3.5 rounded-lg border text-xs ${
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

                  {/* Ask Coach Input */}
                  <div className="space-y-2.5 pt-2 border-t border-surface-border">
                    <textarea
                      rows={2}
                      value={coachUserMessage}
                      onChange={(e) => setCoachUserMessage(e.target.value)}
                      placeholder="Ask the mentor about your current approach or edge case..."
                      className="w-full px-3 py-2 text-xs bg-white border border-surface-border rounded-md text-ink focus:outline-none focus:ring-1 focus:ring-lime-500"
                    />

                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-ink-subtle">
                        {coachLevel > 4 ? 'Max level reached' : `Next hint: Level ${coachLevel}`}
                      </span>

                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        onClick={() => handleRequestCoachHint(coachLevel)}
                        isLoading={isCoachLoading}
                        className="flex items-center gap-1.5 text-xs font-semibold"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>
                          {coachHistory.length === 0
                            ? 'Request Level 1 Hint'
                            : coachUserMessage.trim()
                            ? 'Ask Coach'
                            : `Request Level ${coachLevel} Hint`}
                        </span>
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: Submissions History */}
              {leftTab === 'submissions' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-ink uppercase tracking-wider">
                      Submission History ({problemSubmissions.length})
                    </h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={fetchSubmissions}
                      isLoading={loadingSubmissions}
                      className="text-xs"
                    >
                      Refresh
                    </Button>
                  </div>

                  {problemSubmissions.length === 0 ? (
                    <div className="p-8 text-center text-ink-muted border border-dashed border-surface-border rounded-lg space-y-2">
                      <Clock className="w-6 h-6 text-ink-subtle mx-auto" />
                      <p className="text-xs">No submissions yet for this problem.</p>
                      <p className="text-[11px] text-ink-faint">
                        Click the green <strong>Submit</strong> button in the editor to record a verified submission.
                      </p>
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-lg border border-surface-border">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-surface-subtle text-[11px] font-semibold text-ink-subtle border-b border-surface-border">
                          <tr>
                            <th className="py-2.5 px-3">Status</th>
                            <th className="py-2.5 px-3">Language</th>
                            <th className="py-2.5 px-3">Runtime</th>
                            <th className="py-2.5 px-3">Passed</th>
                            <th className="py-2.5 px-3">Submitted</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-surface-border">
                          {problemSubmissions.map((sub) => (
                            <tr key={sub.id} className="hover:bg-surface-warm/50">
                              <td className="py-2.5 px-3">
                                <Badge
                                  variant={
                                    sub.status === 'passed'
                                      ? 'emerald'
                                      : sub.status === 'failed'
                                      ? 'rose'
                                      : 'zinc'
                                  }
                                  size="sm"
                                  className="capitalize font-mono text-[10px]"
                                >
                                  {sub.status === 'passed' ? 'Accepted' : sub.status}
                                </Badge>
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] capitalize text-ink">
                                {sub.language}
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-ink-muted">
                                {sub.execution_time_ms}ms
                              </td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-ink-muted">
                                {sub.tests_passed}/{sub.tests_total}
                              </td>
                              <td className="py-2.5 px-3 text-[11px] text-ink-subtle">
                                {new Date(sub.created_at).toLocaleDateString(undefined, {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Panel>

          {/* Resizable Divider */}
          <PanelResizeHandle className="w-1.5 bg-surface-border hover:bg-lime-500 transition-colors cursor-col-resize" />

          {/* RIGHT PANEL: Monaco Editor + Collapsible LeetCode Console (55% default) */}
          <Panel defaultSize={55} minSize={35} className="bg-white flex flex-col h-full">
            {/* Editor Toolbar Header */}
            <div className="h-10 px-4 border-b border-surface-border flex items-center justify-between bg-surface-warm/50 flex-shrink-0">
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
                    {lang === 'python' ? 'Python 3' : lang === 'java' ? 'Java 21' : 'C++ 17'}
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyCode}
                  title="Copy code to clipboard"
                  className="text-xs gap-1"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>{copyCodeSuccess ? 'Copied!' : 'Copy'}</span>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetCode}
                  title="Reset to starter code"
                  className="text-xs gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Reset</span>
                </Button>
              </div>
            </div>

            {/* Monaco Editor */}
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

            {/* Collapsible LeetCode Console Drawer */}
            {isConsoleOpen && (
              <div className="h-60 border-t border-surface-border bg-white flex flex-col flex-shrink-0">
                {/* Console Drawer Tab Header */}
                <div className="h-9 px-4 border-b border-surface-border flex items-center justify-between bg-surface-warm/40 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setConsoleTab('testcase')}
                      className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
                        consoleTab === 'testcase'
                          ? 'bg-white text-ink shadow-xs border border-surface-border'
                          : 'text-ink-muted hover:text-ink'
                      }`}
                    >
                      Testcase
                    </button>
                    <button
                      onClick={() => setConsoleTab('result')}
                      className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-colors ${
                        consoleTab === 'result'
                          ? 'bg-white text-ink shadow-xs border border-surface-border'
                          : 'text-ink-muted hover:text-ink'
                      }`}
                    >
                      <span>Test Result</span>
                      {executionResult && (
                        <span
                          className={`w-2 h-2 rounded-full ${
                            executionResult.status === 'passed'
                              ? 'bg-emerald-500'
                              : 'bg-rose-500'
                          }`}
                        />
                      )}
                    </button>
                  </div>

                  <button
                    onClick={() => setIsConsoleOpen(false)}
                    className="text-ink-subtle hover:text-ink text-xs flex items-center gap-1"
                    title="Collapse console"
                  >
                    <span>Console</span>
                    <ChevronDown className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Console Drawer Body */}
                <div className="flex-1 overflow-y-auto p-4 text-xs">
                  {/* TAB: Testcase */}
                  {consoleTab === 'testcase' && (
                    <div className="space-y-3">
                      {/* Case selector pills */}
                      <div className="flex items-center gap-2">
                        {selectedProblem?.sample_test_cases.map((_, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setIsCustomCase(false);
                              setSelectedCaseIndex(idx);
                            }}
                            className={`px-2.5 py-1 text-xs font-mono font-medium rounded-md transition-colors ${
                              !isCustomCase && selectedCaseIndex === idx
                                ? 'bg-zinc-800 text-white font-semibold'
                                : 'bg-surface-subtle text-ink-muted hover:bg-surface-warm border border-surface-border'
                            }`}
                          >
                            Case {idx + 1}
                          </button>
                        ))}

                        <button
                          onClick={() => setIsCustomCase(true)}
                          className={`px-2.5 py-1 text-xs font-mono font-medium rounded-md transition-colors ${
                            isCustomCase
                              ? 'bg-zinc-800 text-white font-semibold'
                              : 'bg-surface-subtle text-ink-muted hover:bg-surface-warm border border-surface-border'
                          }`}
                        >
                          + Custom Testcase
                        </button>
                      </div>

                      {/* Case Input View */}
                      {isCustomCase ? (
                        <div className="space-y-1.5">
                          <label className="text-[11px] font-semibold text-ink-subtle uppercase tracking-wider block">
                            Custom Stdin:
                          </label>
                          <textarea
                            rows={3}
                            value={customStdin}
                            onChange={(e) => setCustomStdin(e.target.value)}
                            placeholder="Enter custom stdin testcase..."
                            className="w-full p-2.5 font-mono text-xs bg-surface-subtle border border-surface-border rounded-lg text-ink focus:outline-none focus:ring-1 focus:ring-lime-500"
                          />
                        </div>
                      ) : (
                        selectedProblem && (
                          <div className="space-y-2 font-mono text-[11px]">
                            <div>
                              <span className="text-ink-subtle block mb-1">stdin:</span>
                              <pre className="p-2.5 bg-surface-subtle border border-surface-border rounded-lg text-ink whitespace-pre-wrap">
                                {selectedProblem.sample_test_cases[selectedCaseIndex]?.stdin.trim() || ''}
                              </pre>
                            </div>
                            <div>
                              <span className="text-ink-subtle block mb-1">expected stdout:</span>
                              <pre className="p-2.5 bg-surface-subtle border border-surface-border rounded-lg text-ink whitespace-pre-wrap">
                                {selectedProblem.sample_test_cases[selectedCaseIndex]?.expected_stdout.trim() || ''}
                              </pre>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}

                  {/* TAB: Test Result */}
                  {consoleTab === 'result' && (
                    <div>
                      {executionError && (
                        <div className="p-3 mb-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-center justify-between">
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
                        <div className="py-8 text-center">
                          <div className="w-6 h-6 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                          <p className="text-xs text-ink-muted">
                            {isRunning
                              ? 'Executing in Bubblewrap sandbox...'
                              : 'Verifying against complete test suite...'}
                          </p>
                        </div>
                      ) : executionResult ? (
                        <div className="space-y-3">
                          {/* Top Status Banner */}
                          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                            <div className="flex items-center gap-2">
                              {submissionSuccess ? (
                                <span className="text-emerald-700 font-bold flex items-center gap-1.5 text-sm">
                                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                  Accepted
                                </span>
                              ) : executionResult.status === 'passed' ? (
                                <span className="text-emerald-700 font-bold flex items-center gap-1.5 text-sm">
                                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                  Sample Tests Passed
                                </span>
                              ) : executionResult.status === 'compile_error' ? (
                                <span className="text-rose-700 font-bold flex items-center gap-1.5 text-sm">
                                  <AlertCircle className="w-4 h-4 text-rose-600" />
                                  Compile Error
                                </span>
                              ) : (
                                <span className="text-rose-700 font-bold flex items-center gap-1.5 text-sm">
                                  <XCircle className="w-4 h-4 text-rose-600" />
                                  Wrong Answer
                                </span>
                              )}
                              <span className="text-ink-subtle">•</span>
                              <span className="font-mono text-ink-muted text-xs">
                                Runtime: {executionResult.execution_time_ms} ms
                              </span>
                            </div>

                            <span className="text-xs font-mono text-ink-subtle">
                              Passed {executionResult.total_passed} / {executionResult.total_tests}
                            </span>
                          </div>

                          {/* Compile error stderr */}
                          {executionResult.status === 'compile_error' && (
                            <pre className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 font-mono text-[11px] whitespace-pre-wrap overflow-x-auto">
                              {executionResult.stderr}
                            </pre>
                          )}

                          {/* Case pills & details */}
                          {executionResult.test_results && executionResult.test_results.length > 0 && (
                            <div className="space-y-3">
                              <div className="flex items-center gap-2">
                                {executionResult.test_results.map((tc, idx) => (
                                  <button
                                    key={idx}
                                    onClick={() => setSelectedCaseIndex(idx)}
                                    className={`px-2.5 py-1 text-xs font-mono font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                                      selectedCaseIndex === idx
                                        ? 'bg-zinc-800 text-white font-semibold'
                                        : 'bg-surface-subtle text-ink-muted hover:bg-surface-warm border border-surface-border'
                                    }`}
                                  >
                                    <span
                                      className={`w-1.5 h-1.5 rounded-full ${
                                        tc.passed ? 'bg-emerald-400' : 'bg-rose-400'
                                      }`}
                                    />
                                    <span>Case {idx + 1}</span>
                                  </button>
                                ))}
                              </div>

                              {/* Selected Case Detail */}
                              {executionResult.test_results[selectedCaseIndex] && (
                                <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border font-mono text-[11px] space-y-1.5">
                                  <div>
                                    <span className="text-ink-subtle">Input:</span>{' '}
                                    <span className="text-ink">
                                      {executionResult.test_results[selectedCaseIndex].stdin?.trim() || ''}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-ink-subtle">Output:</span>{' '}
                                    <span
                                      className={
                                        executionResult.test_results[selectedCaseIndex].passed
                                          ? 'text-ink'
                                          : 'text-rose-700 font-semibold'
                                      }
                                    >
                                      {executionResult.test_results[selectedCaseIndex].actual_stdout?.trim() ||
                                        '<empty>'}
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-ink-subtle">Expected:</span>{' '}
                                    <span className="text-ink">
                                      {executionResult.test_results[selectedCaseIndex].expected_stdout?.trim() ||
                                        ''}
                                    </span>
                                  </div>
                                  {executionResult.test_results[selectedCaseIndex].stderr && (
                                    <div className="text-rose-600 pt-1 border-t border-surface-border">
                                      {executionResult.test_results[selectedCaseIndex].stderr}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="py-8 text-center text-ink-muted text-xs">
                          Click <strong>Run</strong> or <strong>Submit</strong> to evaluate code execution.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Sticky Bottom Action Bar */}
            <div className="h-12 px-4 border-t border-surface-border bg-white flex items-center justify-between flex-shrink-0">
              {/* Left: Console toggle */}
              <button
                onClick={() => setIsConsoleOpen(!isConsoleOpen)}
                className="flex items-center gap-1.5 text-xs font-medium text-ink-muted hover:text-ink px-2.5 py-1.5 rounded-md hover:bg-surface-subtle transition-colors"
              >
                <Terminal className="w-4 h-4 text-lime-700" />
                <span>Console</span>
                {isConsoleOpen ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronUp className="w-3.5 h-3.5" />
                )}
              </button>

              {/* Right: Run and Submit buttons */}
              <div className="flex items-center gap-2.5">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleRunCode}
                  isLoading={isRunning}
                  disabled={isSubmitting}
                  className="gap-1.5 text-xs font-semibold px-4"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run</span>
                </Button>

                {/* LeetCode Green Submit Button */}
                <button
                  type="button"
                  onClick={handleSubmitSolution}
                  disabled={isRunning || isSubmitting}
                  className="h-8 px-5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Send className="w-3.5 h-3.5" />
                  )}
                  <span>Submit</span>
                </button>
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};
