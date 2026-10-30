import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { api } from '../../lib/api';
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  Send,
  FileText,
  Folder,
  FileCode,
  RotateCcw,
  Terminal,
  ChevronDown,
  ChevronUp,
  Lock,
  ArrowLeft,
  X,
} from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { PromptAnalysisModal, PromptAnalysisData } from './PromptAnalysisModal';

interface ProjectDetail {
  id: string;
  title: string;
  slug: string;
  difficulty: 'junior' | 'mid' | 'senior' | 'staff';
  estimated_minutes: number;
  description_markdown: string;
  repository_files: Record<string, string>;
  editable_files: string[];
  active_file: string;
  instructions: string;
  domain: string;
}

interface TestCaseResult {
  name: string;
  status: 'passed' | 'failed';
  duration_ms: number;
  error_message?: string;
  traceback?: string;
}

interface TestRunResponse {
  status: 'passed' | 'failed' | 'error';
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  duration_ms: number;
  test_results: TestCaseResult[];
  raw_output: string;
}

interface CopilotMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: number;
}

export const ProjectWorkspacePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Virtual Filesystem State: filepath -> content
  const [files, setFiles] = useState<Record<string, string>>({});
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string>('');

  // 25-minute Countdown Timer (1500 seconds)
  const [timeRemaining, setTimeRemaining] = useState<number>(25 * 60);
  const [timerRunning, setTimerRunning] = useState<boolean>(true);
  const [timeSpentSeconds, setTimeSpentSeconds] = useState<number>(0);

  // Test Runner State
  const [isRunningTests, setIsRunningTests] = useState<boolean>(false);
  const [testResults, setTestResults] = useState<TestRunResponse | null>(null);
  const [isConsoleOpen, setIsConsoleOpen] = useState<boolean>(true);
  const [consoleTab, setConsoleTab] = useState<'tests' | 'terminal'>('tests');
  const [expandedTest, setExpandedTest] = useState<string | null>(null);

  // Read-Only Copilot State
  const [copilotHistory, setCopilotHistory] = useState<CopilotMessage[]>([
    {
      role: 'assistant',
      content:
        'I am your AI pair programmer. I have **read-only access** to the repository and your current working buffer. ' +
        'I cannot write or edit files directly, but I can diagnose failures, explain architectures, and provide targeted snippets. ' +
        'What are you looking to tackle first?',
      timestamp: Date.now(),
    },
  ]);
  const [copilotInput, setCopilotInput] = useState<string>('');
  const [isCopilotLoading, setIsCopilotLoading] = useState<boolean>(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Left sidebar tab: 'files' | 'spec'
  const [leftTab, setLeftTab] = useState<'files' | 'spec'>('files');

  // Submission & Analysis Modal
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [analysisModalOpen, setAnalysisModalOpen] = useState<boolean>(false);
  const [promptAnalysis, setPromptAnalysis] = useState<PromptAnalysisData | null>(null);

  // Load project data
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<ProjectDetail>(`/projects/${id}`)
      .then((data) => {
        setProject(data);
        setFiles(data.repository_files);
        setActiveFile(data.active_file);
        setOpenTabs([data.active_file, 'README.md']);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load project:', err);
        setLoading(false);
      });
  }, [id]);

  // 25-Minute Countdown Timer Hook
  useEffect(() => {
    if (!timerRunning) return;
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setTimerRunning(false);
          // Auto submit when time expires
          handleTriggerSubmission();
          return 0;
        }
        return prev - 1;
      });
      setTimeSpentSeconds((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [timerRunning]);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [copilotHistory, isCopilotLoading]);

  // Format time MM:SS
  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Switch or open file in tabs
  const handleOpenFile = (path: string) => {
    if (!openTabs.includes(path)) {
      setOpenTabs([...openTabs, path]);
    }
    setActiveFile(path);
  };

  // Close tab
  const handleCloseTab = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = openTabs.filter((t) => t !== path);
    setOpenTabs(updated);
    if (activeFile === path) {
      if (updated.length > 0) {
        setActiveFile(updated[updated.length - 1]);
      } else {
        setActiveFile('');
      }
    }
  };

  // Update file buffer
  const handleFileChange = (newContent: string) => {
    if (!activeFile) return;
    setFiles((prev) => ({
      ...prev,
      [activeFile]: newContent,
    }));
  };

  // Reset to starter code
  const handleResetActiveFile = () => {
    if (!project || !activeFile) return;
    if (confirm(`Reset ${activeFile} back to its original starter code?`)) {
      setFiles((prev) => ({
        ...prev,
        [activeFile]: project.repository_files[activeFile] || '',
      }));
    }
  };

  // Run CI/CD Tests
  const handleRunTests = async () => {
    if (!project) return;
    setIsRunningTests(true);
    setIsConsoleOpen(true);
    try {
      const res = await api.post<TestRunResponse>(`/projects/${project.id}/run-tests`, {
        files,
      });
      setTestResults(res);
      setConsoleTab('tests');
    } catch (err: any) {
      console.error('Failed to run tests:', err);
    } finally {
      setIsRunningTests(false);
    }
  };

  // Send Copilot Message
  const handleSendCopilot = async (overridePrompt?: string) => {
    const textToSend = overridePrompt || copilotInput;
    if (!textToSend.trim() || !project || isCopilotLoading) return;

    const userMsg: CopilotMessage = {
      role: 'user',
      content: textToSend.trim(),
      timestamp: Date.now(),
    };

    setCopilotHistory((prev) => [...prev, userMsg]);
    setCopilotInput('');
    setIsCopilotLoading(true);

    try {
      const res = await api.post<{ message: string; tokens_used: number }>(
        `/projects/${project.id}/copilot`,
        {
          files,
          active_file: activeFile,
          message: textToSend.trim(),
          conversation_history: copilotHistory.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          last_test_results: testResults
            ? {
                passed_tests: testResults.passed_tests,
                total_tests: testResults.total_tests,
                raw_output: testResults.raw_output,
              }
            : null,
        }
      );

      setCopilotHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.message,
          timestamp: Date.now(),
        },
      ]);
    } catch (err) {
      console.error('Copilot request failed:', err);
      setCopilotHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Failed to contact Copilot assistant. Please check your connection and try again.',
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsCopilotLoading(false);
    }
  };

  // Trigger submission and prompt analysis
  const handleTriggerSubmission = async () => {
    if (!project) return;
    setIsSubmitting(true);
    try {
      const res = await api.post<any>(`/projects/${project.id}/submit`, {
        files,
        conversation_history: copilotHistory.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        time_spent_seconds: timeSpentSeconds,
      });

      setPromptAnalysis(res.prompt_analysis);
      setAnalysisModalOpen(true);
    } catch (err) {
      console.error('Submission failed:', err);
      alert('Failed to submit project. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || !project) {
    return (
      <div className="min-h-screen bg-surface-warm flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
        <span className="text-xs text-slate-500 font-mono">Provisioning virtual project workspace...</span>
      </div>
    );
  }

  const isEditable = project.editable_files.includes(activeFile);
  const currentContent = files[activeFile] ?? '';

  // Timer Color styling
  const isTimeCritical = timeRemaining <= 120; // < 2 min
  const isTimeWarning = timeRemaining <= 300 && !isTimeCritical; // < 5 min

  return (
    <div className="h-screen flex flex-col bg-surface-warm font-sans text-slate-900 overflow-hidden">
      {/* TOP WORKSPACE NAVIGATION BAR */}
      <header className="h-13 bg-white border-b border-slate-200/80 px-4 flex items-center justify-between shrink-0 z-10 shadow-xs">
        {/* Left: Back button & Project Title */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/projects')}
            className="flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 px-2 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Projects</span>
          </button>

          <div className="h-4 w-px bg-slate-200" />

          <div className="flex items-center gap-2">
            <span className="font-bold text-sm text-slate-900 tracking-tight">{project.title}</span>
            <Badge variant="zinc" size="sm" className="hidden md:inline-block font-mono text-[10px]">
              {project.domain}
            </Badge>
          </div>
        </div>

        {/* Center: 25-Minute Countdown Timer */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold transition-all ${
              isTimeCritical
                ? 'bg-rose-100 text-rose-800 border border-rose-300 animate-pulse'
                : isTimeWarning
                ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse'
                : 'bg-slate-100 text-slate-700 border border-slate-200'
            }`}
            title="Interview countdown timer"
          >
            <Clock className={`w-3.5 h-3.5 ${isTimeCritical ? 'text-rose-600' : 'text-slate-500'}`} />
            <span>{formatTimer(timeRemaining)}</span>
          </div>
        </div>

        {/* Right: Actions (Run Tests & Submit) */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRunTests}
            isLoading={isRunningTests}
            className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Run CI/CD Tests</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={handleTriggerSubmission}
            isLoading={isSubmitting}
            className="flex items-center gap-1.5 text-xs font-semibold shadow-sm"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Submit & Analyze Prompts</span>
          </Button>
        </div>
      </header>

      {/* THREE-PANEL RESIZABLE DESKTOP IDE */}
      <div className="flex-1 min-h-0">
        <PanelGroup orientation="horizontal" className="h-full">
          {/* LEFT PANEL: File Explorer & Problem Spec (20% default) */}
          <Panel defaultSize={20} minSize={15} maxSize={30} className="bg-white border-r border-slate-200/80 flex flex-col h-full min-w-0 overflow-hidden">
            {/* Tab switch header */}
            <div className="h-10 border-b border-slate-200/80 px-2 flex items-center gap-1 bg-slate-50/60 shrink-0">
              <button
                onClick={() => setLeftTab('files')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  leftTab === 'files'
                    ? 'bg-white text-indigo-700 font-semibold shadow-xs border border-slate-200/60'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Folder className="w-3.5 h-3.5" />
                <span>Files</span>
              </button>
              <button
                onClick={() => setLeftTab('spec')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  leftTab === 'spec'
                    ? 'bg-white text-indigo-700 font-semibold shadow-xs border border-slate-200/60'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Specification</span>
              </button>
            </div>

            {/* Left Content Area */}
            <div className="flex-1 overflow-y-auto p-3">
              {leftTab === 'files' ? (
                <div className="space-y-1">
                  <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-2 py-1">
                    Repository Tree
                  </div>
                  {Object.keys(files).map((filePath) => {
                    const isFileEditable = project.editable_files.includes(filePath);
                    const isActive = activeFile === filePath;

                    return (
                      <button
                        key={filePath}
                        onClick={() => handleOpenFile(filePath)}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono flex items-center justify-between transition-colors ${
                          isActive
                            ? 'bg-indigo-50 text-indigo-900 font-semibold border border-indigo-200/60'
                            : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <FileCode
                            className={`w-3.5 h-3.5 shrink-0 ${
                              isFileEditable ? 'text-emerald-600' : 'text-slate-400'
                            }`}
                          />
                          <span className="truncate">{filePath}</span>
                        </div>
                        {isFileEditable ? (
                          <span className="text-[9px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200/60 uppercase">
                            Editable
                          </span>
                        ) : (
                          <span className="text-[9px] font-semibold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded uppercase">
                            Lock
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="prose prose-sm max-w-none text-xs text-slate-700 space-y-3">
                  <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 text-indigo-950 font-medium">
                    {project.instructions}
                  </div>
                  <pre className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-[11px] font-mono whitespace-pre-wrap text-slate-800">
                    {project.description_markdown}
                  </pre>
                </div>
              )}
            </div>
          </Panel>

          {/* Left Resize Handle */}
          <PanelResizeHandle className="w-1.5 bg-slate-200 hover:bg-indigo-500 transition-colors cursor-col-resize" />

          {/* CENTER PANEL: Monaco Multi-Tab Editor + Bottom CI/CD Drawer (52% default) */}
          <Panel defaultSize={52} minSize={35} className="bg-white flex flex-col h-full min-w-0 overflow-hidden">
            {/* Tab Bar Header */}
            <div className="h-10 border-b border-slate-200/80 px-2 flex items-center justify-between bg-slate-50/60 shrink-0">
              <div className="flex items-center gap-1 overflow-x-auto">
                {openTabs.map((tab) => {
                  const isCurrent = activeFile === tab;
                  const isTabEditable = project.editable_files.includes(tab);

                  return (
                    <div
                      key={tab}
                      onClick={() => setActiveFile(tab)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono cursor-pointer transition-colors ${
                        isCurrent
                          ? 'bg-white text-indigo-900 font-semibold shadow-xs border border-slate-200/80'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                      }`}
                    >
                      <FileCode
                        className={`w-3.5 h-3.5 ${
                          isTabEditable ? 'text-emerald-600' : 'text-slate-400'
                        }`}
                      />
                      <span>{tab.split('/').pop()}</span>
                      <button
                        onClick={(e) => handleCloseTab(tab, e)}
                        className="p-0.5 rounded hover:bg-slate-200 text-slate-400 hover:text-slate-700"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>

              {isEditable && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleResetActiveFile}
                  title="Reset file to starter code"
                  className="text-[11px] gap-1 text-slate-500 hover:text-slate-900"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset</span>
                </Button>
              )}
            </div>

            {/* Read-Only Notice Banner */}
            {!isEditable && activeFile && (
              <div className="bg-slate-100/80 border-b border-slate-200 px-3 py-1.5 flex items-center justify-between text-xs text-slate-600">
                <div className="flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                  <span>
                    <strong>{activeFile}</strong> is part of the test infrastructure and is read-only.
                  </span>
                </div>
                <button
                  onClick={() => handleOpenFile(project.active_file)}
                  className="text-indigo-600 font-semibold hover:underline text-[11px]"
                >
                  Edit {project.active_file}
                </button>
              </div>
            )}

            {/* Monaco Editor Canvas */}
            <div className="flex-1 min-h-0 relative">
              <Editor
                height="100%"
                language={activeFile.endsWith('.py') ? 'python' : activeFile.endsWith('.md') ? 'markdown' : 'plaintext'}
                theme="vs"
                value={currentContent}
                onChange={(val) => handleFileChange(val || '')}
                options={{
                  readOnly: !isEditable,
                  minimap: { enabled: false },
                  fontSize: 13,
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 4,
                  renderLineHighlight: 'all',
                  fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, monospace",
                }}
              />
            </div>

            {/* BOTTOM CI/CD TEST RESULTS DRAWER */}
            <div
              className={`border-t border-slate-200 bg-white flex flex-col transition-all duration-200 shrink-0 ${
                isConsoleOpen ? 'h-64' : 'h-10'
              }`}
            >
              {/* Drawer Header Toolbar */}
              <div
                onClick={() => setIsConsoleOpen(!isConsoleOpen)}
                className="h-10 px-4 bg-slate-50 border-b border-slate-200/80 flex items-center justify-between cursor-pointer select-none"
              >
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-slate-700 uppercase tracking-wider">
                    <Terminal className="w-3.5 h-3.5 text-indigo-600" />
                    <span>CI/CD Test Runner</span>
                  </div>

                  {testResults && (
                    <Badge
                      variant={
                        testResults.status === 'passed'
                          ? 'emerald'
                          : testResults.status === 'failed'
                          ? 'rose'
                          : 'zinc'
                      }
                      size="sm"
                      className="font-mono text-[10px]"
                    >
                      {testResults.passed_tests} / {testResults.total_tests} Tests Passed (
                      {(testResults.duration_ms / 1000).toFixed(2)}s)
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {isConsoleOpen && (
                    <div
                      className="flex items-center gap-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => setConsoleTab('tests')}
                        className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                          consoleTab === 'tests'
                            ? 'bg-white text-indigo-700 font-semibold shadow-xs border border-slate-200'
                            : 'text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        Test Cases
                      </button>
                      <button
                        onClick={() => setConsoleTab('terminal')}
                        className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                          consoleTab === 'terminal'
                            ? 'bg-white text-indigo-700 font-semibold shadow-xs border border-slate-200'
                            : 'text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        Terminal Output
                      </button>
                    </div>
                  )}

                  <button className="text-slate-400 hover:text-slate-600">
                    {isConsoleOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Drawer Body */}
              {isConsoleOpen && (
                <div className="flex-1 overflow-y-auto p-4 bg-slate-50/50 font-mono text-xs">
                  {isRunningTests ? (
                    <div className="h-full flex flex-col items-center justify-center space-y-2">
                      <div className="w-6 h-6 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
                      <span className="text-xs text-slate-500">
                        Executing multi-file test harness inside isolated sandbox...
                      </span>
                    </div>
                  ) : !testResults ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-2">
                      <Terminal className="w-8 h-8 stroke-[1.5]" />
                      <span>Click &ldquo;Run CI/CD Tests&rdquo; to execute the Pytest test suite.</span>
                    </div>
                  ) : consoleTab === 'tests' ? (
                    <div className="space-y-2">
                      {testResults.test_results.map((tr) => {
                        const isExpanded = expandedTest === tr.name;
                        return (
                          <div
                            key={tr.name}
                            className={`p-3 rounded-lg border transition-all ${
                              tr.status === 'passed'
                                ? 'bg-white border-slate-200/80'
                                : 'bg-rose-50/40 border-rose-200/80'
                            }`}
                          >
                            <div
                              onClick={() => setExpandedTest(isExpanded ? null : tr.name)}
                              className="flex items-center justify-between cursor-pointer"
                            >
                              <div className="flex items-center gap-2">
                                {tr.status === 'passed' ? (
                                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
                                )}
                                <span
                                  className={`font-semibold ${
                                    tr.status === 'passed' ? 'text-slate-800' : 'text-rose-900'
                                  }`}
                                >
                                  {tr.name}
                                </span>
                              </div>
                              <span className="text-[11px] text-slate-400">
                                {tr.status === 'passed' ? 'PASSED' : 'FAILED [Click for Trace]'}
                              </span>
                            </div>

                            {/* Failure details */}
                            {tr.status === 'failed' && isExpanded && (
                              <div className="mt-2 pt-2 border-t border-rose-200/60 space-y-1.5 text-[11px]">
                                {tr.error_message && (
                                  <div className="text-rose-800 font-bold bg-rose-100/60 p-2 rounded">
                                    {tr.error_message}
                                  </div>
                                )}
                                {tr.traceback && (
                                  <pre className="text-slate-700 bg-white p-2.5 rounded border border-rose-200 whitespace-pre-wrap overflow-x-auto">
                                    {tr.traceback}
                                  </pre>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <pre className="whitespace-pre-wrap bg-slate-900 text-slate-100 p-4 rounded-xl text-[11px] overflow-x-auto">
                      {testResults.raw_output}
                    </pre>
                  )}
                </div>
              )}
            </div>
          </Panel>

          {/* Right Resize Handle */}
          <PanelResizeHandle className="w-1.5 bg-slate-200 hover:bg-indigo-500 transition-colors cursor-col-resize" />

          {/* RIGHT PANEL: Read-Only AI Pair Programmer (28% default) */}
          <Panel defaultSize={28} minSize={20} maxSize={40} className="bg-white border-l border-slate-200/80 flex flex-col h-full min-w-0 overflow-hidden">
            {/* Copilot Header */}
            <div className="p-3 border-b border-slate-200/80 bg-slate-50/60 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-bold text-xs text-slate-900 leading-tight">AI Pair Programmer</div>
                  <div className="text-[10px] text-slate-500">Read-Only Guardrail Active</div>
                </div>
              </div>
              <Badge variant="indigo" size="sm" className="font-mono text-[9px] uppercase">
                Read-Only
              </Badge>
            </div>

            {/* Quick Prompt Suggestion Chips */}
            <div className="p-2 border-b border-slate-100 flex items-center gap-1.5 overflow-x-auto bg-slate-50/30 text-[10px]">
              <button
                onClick={() => handleSendCopilot('Explain the architecture and how these files connect.')}
                className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-300 transition-colors shrink-0"
              >
                Explain Architecture
              </button>
              <button
                onClick={() => handleSendCopilot('Why is my test failing? How do I fix it?')}
                className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-300 transition-colors shrink-0"
              >
                Why is test failing?
              </button>
              <button
                onClick={() => handleSendCopilot('Where in the code should I start?')}
                className="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:text-indigo-600 hover:border-indigo-300 transition-colors shrink-0"
              >
                Where do I start?
              </button>
            </div>

            {/* Chat Transcript Area */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {copilotHistory.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-xl text-xs space-y-1.5 ${
                    msg.role === 'user'
                      ? 'bg-slate-100 text-slate-900 ml-4 border border-slate-200/60'
                      : 'bg-indigo-50/50 text-slate-800 mr-2 border border-indigo-100'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-semibold">
                    <span className={msg.role === 'user' ? 'text-slate-500' : 'text-indigo-700'}>
                      {msg.role === 'user' ? 'You' : 'Copilot Mentor'}
                    </span>
                  </div>
                  <div className="prose prose-xs max-w-none text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                    {msg.content}
                  </div>
                </div>
              ))}

              {isCopilotLoading && (
                <div className="p-3 rounded-xl bg-indigo-50/30 border border-indigo-100 flex items-center gap-2 text-xs text-indigo-700">
                  <div className="w-3.5 h-3.5 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin" />
                  <span>Reviewing workspace files in read-only mode...</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Chat Input Area */}
            <div className="p-3 border-t border-slate-200/80 bg-white space-y-2 shrink-0">
              <textarea
                rows={2}
                value={copilotInput}
                onChange={(e) => setCopilotInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendCopilot();
                  }
                }}
                placeholder="Ask about architecture, trade-offs, or errors..."
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200/80 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none font-sans"
              />
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400">Shift+Enter for newline</span>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleSendCopilot()}
                  isLoading={isCopilotLoading}
                  className="gap-1 text-xs"
                >
                  <span>Send</span>
                  <Send className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </Panel>
        </PanelGroup>
      </div>

      {/* POST-SUBMISSION PROMPT ANALYSIS MODAL */}
      <PromptAnalysisModal
        isOpen={analysisModalOpen}
        onClose={() => setAnalysisModalOpen(false)}
        data={promptAnalysis}
        testsPassed={testResults?.passed_tests ?? 0}
        totalTests={testResults?.total_tests ?? 6}
        timeSpentSeconds={timeSpentSeconds}
        onRestart={() => {
          setAnalysisModalOpen(false);
          navigate('/projects');
        }}
      />
    </div>
  );
};
