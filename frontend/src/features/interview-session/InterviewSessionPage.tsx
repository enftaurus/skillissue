import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../../lib/api';
import {
  Interview,
  InterviewMessage,
  RubricDimension,
  CodeExecutionResult,
  CodingProblem,
  HintResponse,
} from '../../lib/types';
import { SpeechHandler } from '../../lib/speech';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { SelfEvaluationModal } from './SelfEvaluationModal';
import { InterviewerAvatar } from './InterviewerAvatar';
import {
  AlertTriangle,
  Code2,
  Lightbulb,
  LogOut,
  Mic,
  MicOff,
  Play,
  RotateCcw,
  Send,
  Terminal,
  Volume2,
  VolumeX,
} from 'lucide-react';

export const InterviewSessionPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [interview, setInterview] = useState<Interview | null>(null);
  const [messages, setMessages] = useState<InterviewMessage[]>([]);
  const [rubrics, setRubrics] = useState<RubricDimension[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Speech Recognition & TTS State
  const [isListening, setIsListening] = useState(false);
  const [isSpeechSupported, setIsSpeechSupported] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const speechHandlerRef = useRef<SpeechHandler | null>(null);

  // Coding Sandbox Pane (for DSA / coding sessions)
  const [showCodeEditor, setShowCodeEditor] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState<'python' | 'java' | 'cpp'>('python');
  const [code, setCode] = useState('');
  const [codingProblem, setCodingProblem] = useState<CodingProblem | null>(null);
  const [executionResult, setExecutionResult] = useState<CodeExecutionResult | null>(null);
  const [isExecutingCode, setIsExecutingCode] = useState(false);

  // Socratic Hint Ladder
  const [hintLevelUsed, setHintLevelUsed] = useState(0);
  const [isRequestingHint, setIsRequestingHint] = useState(false);
  const [showHintMenu, setShowHintMenu] = useState(false);

  // Modal State
  const [showSelfEvalModal, setShowSelfEvalModal] = useState(false);
  const [showExitConfirmModal, setShowExitConfirmModal] = useState(false);
  const [hintError, setHintError] = useState('');
  const [codeExecutionError, setCodeExecutionError] = useState('');
  const [sessionState, setSessionState] = useState<{
    current_topic?: string;
    topic_statuses?: Record<string, string>;
    running_summary?: string;
    turn_count?: number;
  } | null>(null);

  // Elapsed Timer
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const baseInputTextRef = useRef<string>('');
  const codeDraftsRef = useRef<Record<string, string>>({});
  const pendingTurnIdRef = useRef<string | null>(null);

  // 1. Initial Load
  useEffect(() => {
    if (!id) return;

    api.get<Interview>(`/interviews/${id}`)
      .then((data) => {
        setInterview(data);
        setMessages(data.messages || []);
        setHintLevelUsed(data.hint_level_used || 0);

        if (data.category === 'dsa') {
          setShowCodeEditor(true);
          const probId = data.coding_problem_id || 'two-sum';
          api.get<CodingProblem>(`/coding/problems/${probId}`)
            .then((prob) => {
              setCodingProblem(prob);
              const starter = prob.starter_code['python'] || '';
              codeDraftsRef.current['python'] = starter;
              setCode(starter);
            })
            .catch(() => {});
        }

        return api.get<RubricDimension[]>(`/interviews/rubrics/${data.category}`);
      })
      .then((r) => {
        setRubrics(r);
        return api.get<any>(`/interviews/${id}/state`);
      })
      .then(setSessionState)
      .catch((err) => setError(err.message || 'Failed to load interview session.'))
      .finally(() => setLoading(false));

    // Initialize Speech Handler
    const handler = new SpeechHandler(
      (text, isFinal) => {
        if (isFinal) {
          const updated = (baseInputTextRef.current ? `${baseInputTextRef.current} ` : '') + text.trim();
          baseInputTextRef.current = updated;
          setInputText(updated);
        } else {
          const live = (baseInputTextRef.current ? `${baseInputTextRef.current} ` : '') + text;
          setInputText(live);
        }
      },
      (err) => console.warn('Speech recognition notice:', err),
      (listening) => setIsListening(listening)
    );
    speechHandlerRef.current = handler;
    setIsSpeechSupported(handler.isSupported);

    return () => {
      handler.stop();
      SpeechHandler.stopSpeaking();
    };
  }, [id]);

  // Elapsed Timer effect
  useEffect(() => {
    if (interview?.status !== 'in_progress') return;

    const timer = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [interview?.status]);

  // Prevent accidental tab close during live interview
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (interview?.status === 'in_progress') {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [interview?.status]);

  // Auto-scroll transcript
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  // Spacebar Push-To-Talk
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && e.target === document.body && !isListening && isSpeechSupported) {
        e.preventDefault();
        toggleSpeechRecognition();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isListening, isSpeechSupported]);

  const speakWithMicSuppression = useCallback(
    (text: string) => {
      if (!speechHandlerRef.current) return;
      if (isListening) {
        speechHandlerRef.current.stop();
      }
      setIsSpeaking(true);
      SpeechHandler.speak(text, () => {
        setIsSpeaking(false);
      });
    },
    [isListening]
  );

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const content = inputText.trim();
    if (!content || !id || isSending) return;

    if (isListening) {
      speechHandlerRef.current?.stop();
    }

    const clientTurnId =
      pendingTurnIdRef.current ||
      (typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `turn-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`);
    pendingTurnIdRef.current = clientTurnId;

    const optimisticMsg: InterviewMessage = {
      id: `temp-${Date.now()}`,
      interview_id: id,
      role: 'user',
      content,
      question_index: messages.length + 1,
      is_follow_up: false,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMsg]);
    setIsSending(true);
    setError('');

    try {
      const assistantMsg = await api.post<InterviewMessage>(`/interviews/${id}/message`, {
        content,
        client_turn_id: clientTurnId,
      });

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticMsg.id),
        optimisticMsg,
        assistantMsg,
      ]);
      setInputText('');
      baseInputTextRef.current = '';
      pendingTurnIdRef.current = null;

      // Update state snapshot
      api.get<any>(`/interviews/${id}/state`).then(setSessionState).catch(() => {});

      if (autoSpeak) {
        speakWithMicSuppression(assistantMsg.content);
      }
    } catch (err: any) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMsg.id));
      setInputText(content);
      baseInputTextRef.current = content;
      setError(
        err.message || 'Failed to send message. Your draft has been preserved. Please retry.'
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleRequestHint = async (level: number) => {
    if (!id || isRequestingHint) return;
    setIsRequestingHint(true);
    setShowHintMenu(false);
    setHintError('');

    try {
      const res = await api.post<HintResponse>(`/interviews/${id}/hint`, {
        level,
        problem_id: codingProblem?.id,
        current_code: code || undefined,
      });

      setHintLevelUsed(res.total_hint_level_used);

      const updated = await api.get<Interview>(`/interviews/${id}`);
      setMessages(updated.messages || []);

      const assistantHints = (updated.messages || []).filter(
        (m) =>
          m.role === 'assistant' &&
          (m.content.startsWith('[Level') || m.content.startsWith('Mentor Hint:'))
      );
      const latestHint = assistantHints[assistantHints.length - 1];

      if (autoSpeak && latestHint) {
        speakWithMicSuppression(latestHint.content);
      }
    } catch (err: any) {
      setHintError(err.message || 'Failed to retrieve calibrated hint.');
    } finally {
      setIsRequestingHint(false);
    }
  };

  const toggleSpeechRecognition = () => {
    if (!speechHandlerRef.current || !isSpeechSupported) return;

    if (isListening) {
      speechHandlerRef.current.stop();
    } else {
      if (isSpeaking) {
        SpeechHandler.stopSpeaking();
        setIsSpeaking(false);
      }
      baseInputTextRef.current = inputText;
      speechHandlerRef.current.start();
    }
  };

  const handleLanguageChange = (lang: 'python' | 'java' | 'cpp') => {
    if (codingProblem) {
      codeDraftsRef.current[codeLanguage] = code;
      const starter = codingProblem.starter_code[lang] || '';
      const draft = codeDraftsRef.current[lang] || starter;
      setCode(draft);
    }
    setCodeLanguage(lang);
  };

  const handleRunCode = async () => {
    if (!codingProblem || isExecutingCode || !id) return;
    setIsExecutingCode(true);
    setCodeExecutionError('');

    try {
      const res = await api.post<CodeExecutionResult>(`/interviews/${id}/code`, {
        problem_id: codingProblem.id,
        language: codeLanguage,
        code,
        run_mode: 'run',
      });
      setExecutionResult(res);
      const updated = await api.get<Interview>(`/interviews/${id}`);
      setMessages(updated.messages || []);
    } catch (err: any) {
      setCodeExecutionError(err.message || 'Execution failed. Review syntax or memory constraints.');
    } finally {
      setIsExecutingCode(false);
    }
  };

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const assistantCount = messages.filter((m) => m.role === 'assistant').length;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-24 text-center">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-ink-muted">Connecting to interview room...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 space-y-4">
      {/* FOCUS MODE HEADER BAR */}
      <div className="bg-white border border-surface-border rounded-xl px-4 py-3 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Left: Live status & title */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
            </span>
            <span className="text-xs font-bold uppercase tracking-wider text-rose-700">
              Live Interview
            </span>
          </div>

          <span className="text-ink-subtle">•</span>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-ink">{interview?.title}</h1>
              <Badge variant="lime" size="sm" className="font-mono text-[10px] uppercase">
                {interview?.category}
              </Badge>
            </div>
            <div className="text-[11px] text-ink-muted">
              Turn {Math.min(8, assistantCount)} of ~8 · {interview?.target_role} ({interview?.difficulty})
            </div>
          </div>
        </div>

        {/* Right: Controls & Actions */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Elapsed Timer */}
          <div className="font-mono text-xs font-semibold bg-surface-subtle px-2.5 py-1 rounded-md border border-surface-border text-ink">
            ⏱ {formatTime(secondsElapsed)} / {interview?.target_duration_minutes || 20}:00
          </div>

          {/* AI Voice Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoSpeak(!autoSpeak)}
            title={autoSpeak ? 'Mute AI Voice' : 'Enable AI Voice readout'}
            className="text-xs gap-1"
          >
            {autoSpeak ? (
              <Volume2 className="w-4 h-4 text-lime-700" />
            ) : (
              <VolumeX className="w-4 h-4 text-ink-subtle" />
            )}
            <span className="hidden md:inline">{autoSpeak ? 'Voice On' : 'Voice Off'}</span>
          </Button>

          {/* Coding Editor Toggle (for DSA or technical rounds) */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCodeEditor(!showCodeEditor)}
            className="text-xs gap-1.5"
          >
            <Code2 className="w-4 h-4 text-lime-700" />
            <span>{showCodeEditor ? 'Hide Code' : 'Dock Code'}</span>
          </Button>

          {/* Socratic Hint Ladder Menu */}
          <div className="relative">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowHintMenu(!showHintMenu)}
              isLoading={isRequestingHint}
              className="text-xs gap-1.5 border-lime-300"
              title="Request a calibrated Socratic hint from the interviewer"
            >
              <Lightbulb className="w-4 h-4 text-amber-500 fill-amber-400/30" />
              <span>Hint {hintLevelUsed > 0 ? `(L${hintLevelUsed})` : ''}</span>
            </Button>

            {showHintMenu && (
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-surface-border p-2 z-50 text-xs space-y-1">
                <div className="px-2.5 py-1 text-[11px] font-semibold text-ink-subtle uppercase tracking-wider border-b border-surface-border mb-1">
                  Socratic Hint Ladder
                </div>
                <button
                  onClick={() => handleRequestHint(1)}
                  disabled={hintLevelUsed >= 1}
                  className="w-full text-left p-2 rounded-lg hover:bg-surface-subtle disabled:opacity-50 transition-colors"
                >
                  <div className="font-semibold text-ink flex items-center justify-between">
                    <span>Tier 1: Clarifying Nudge</span>
                    <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono">
                      -5%
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-muted">Subtle directional prompt without spoilers.</div>
                </button>
                <button
                  onClick={() => handleRequestHint(2)}
                  disabled={hintLevelUsed >= 2}
                  className="w-full text-left p-2 rounded-lg hover:bg-surface-subtle disabled:opacity-50 transition-colors"
                >
                  <div className="font-semibold text-ink flex items-center justify-between">
                    <span>Tier 2: Pattern Identification</span>
                    <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono">
                      -15%
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-muted">Reveals algorithmic pattern or data structure.</div>
                </button>
                <button
                  onClick={() => handleRequestHint(3)}
                  disabled={hintLevelUsed >= 3}
                  className="w-full text-left p-2 rounded-lg hover:bg-surface-subtle disabled:opacity-50 transition-colors"
                >
                  <div className="font-semibold text-ink flex items-center justify-between">
                    <span>Tier 3: Pseudocode & Logic</span>
                    <span className="text-[10px] text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded font-mono">
                      -30%
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-muted">Step-by-step structural logic walkthrough.</div>
                </button>
              </div>
            )}
          </div>

          {/* End & Self-Evaluate Button */}
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowSelfEvalModal(true)}
            className="text-xs font-semibold"
          >
            End & Self-Evaluate
          </Button>

          {/* Exit Interview Button (Focus Mode exit confirmation) */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowExitConfirmModal(true)}
            className="text-xs text-ink-muted hover:text-rose-700 gap-1"
            title="Exit interview and return to dashboard"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Exit</span>
          </Button>
        </div>
      </div>

      {/* Session State / Competency Inspector Banner */}
      {sessionState && (
        <div className="flex items-center justify-between px-3.5 py-2 bg-surface-warm/80 border border-surface-border rounded-lg text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-ink">Active Competency:</span>
            <span className="font-mono text-lime-800 bg-lime-50 px-2 py-0.5 rounded border border-lime-200">
              {sessionState.current_topic || 'General Engineering Architecture'}
            </span>
            {sessionState.topic_statuses && sessionState.current_topic && (
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                  sessionState.topic_statuses[sessionState.current_topic] === 'assessed'
                    ? 'bg-zinc-100 text-zinc-700'
                    : sessionState.topic_statuses[sessionState.current_topic] === 'needs_follow_up'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-lime-100 text-lime-800'
                }`}
              >
                {sessionState.topic_statuses[sessionState.current_topic] || 'In Progress'}
              </span>
            )}
          </div>
          {sessionState.running_summary && (
            <span
              className="text-[11px] text-ink-subtle hidden md:inline truncate max-w-md"
              title={sessionState.running_summary}
            >
              Interviewer Memory: {sessionState.running_summary}
            </span>
          )}
        </div>
      )}

      {error && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-center justify-between gap-3 shadow-xs">
          <span>{error}</span>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => handleSendMessage()}
            className="shrink-0 text-xs py-1 px-3 border-amber-300 hover:bg-amber-100 font-semibold"
          >
            Retry Send
          </Button>
        </div>
      )}

      {hintError && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg flex items-center justify-between">
          <span>{hintError}</span>
          <button
            onClick={() => setHintError('')}
            className="text-amber-700 hover:text-amber-900 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {codeExecutionError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg flex items-center justify-between">
          <span>{codeExecutionError}</span>
          <button
            onClick={() => setCodeExecutionError('')}
            className="text-rose-700 hover:text-rose-900 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Split Layout: Dialogue & Code Sandbox */}
      <div
        className={`grid gap-5 ${
          showCodeEditor
            ? 'grid-cols-1 lg:grid-cols-12'
            : 'grid-cols-1 lg:grid-cols-12'
        }`}
      >
        {/* Left Column (or Avatar Sidebar in non-docked mode) */}
        {!showCodeEditor && (
          <div className="lg:col-span-4 space-y-4">
            <InterviewerAvatar
              isSpeaking={isSpeaking}
              isListening={isListening}
              isThinking={isSending}
              autoSpeak={autoSpeak}
              onToggleAutoSpeak={() => setAutoSpeak(!autoSpeak)}
              interviewerTitle={`Senior Staff Interviewer (${interview?.target_role || 'Engineering'})`}
              category={interview?.category}
            />

            <Card className="p-4 bg-white border border-surface-border text-xs space-y-2.5">
              <h4 className="font-semibold text-ink uppercase tracking-wider text-[11px]">
                Interview Guidelines
              </h4>
              <ul className="space-y-1.5 text-ink-muted text-[11px]">
                <li className="flex items-start gap-1.5">
                  <span className="text-lime-600 font-bold">•</span>
                  <span>Speak or type directly. Focus on concrete trade-offs and metrics.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-lime-600 font-bold">•</span>
                  <span>Use microphone or push Spacebar for hands-free speech input.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-lime-600 font-bold">•</span>
                  <span>Dock code anytime if asked to sketch algorithms or architectures.</span>
                </li>
              </ul>
            </Card>
          </div>
        )}

        {/* Dialogue Feed Column */}
        <div
          className={`${
            showCodeEditor ? 'lg:col-span-6' : 'lg:col-span-8'
          } space-y-3 flex flex-col`}
        >
          {showCodeEditor && (
            <div className="mb-1">
              <InterviewerAvatar
                isSpeaking={isSpeaking}
                isListening={isListening}
                isThinking={isSending}
                autoSpeak={autoSpeak}
                onToggleAutoSpeak={() => setAutoSpeak(!autoSpeak)}
                interviewerTitle="Senior Staff Interviewer"
                category={interview?.category}
              />
            </div>
          )}

          {/* Dialogue Message Thread */}
          <div className="bg-white border border-surface-border rounded-xl p-4 sm:p-5 shadow-xs min-h-[440px] max-h-[540px] overflow-y-auto space-y-4">
            {messages.map((m, idx) => {
              const isAssistant = m.role === 'assistant';
              const isHintMsg =
                m.content.startsWith('[Level') || m.content.startsWith('[Requested Level');

              return (
                <div
                  key={m.id || idx}
                  className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'}`}
                >
                  <div className="flex items-center gap-1.5 mb-1 px-1">
                    <span className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider">
                      {isAssistant ? 'Interviewer' : 'You'}
                    </span>
                    {isHintMsg && (
                      <span className="text-[9px] font-mono px-1 rounded bg-amber-100 text-amber-800 font-medium">
                        SOCRATIC HINT
                      </span>
                    )}
                  </div>

                  <div
                    className={`max-w-[90%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-xs ${
                      isAssistant
                        ? isHintMsg
                          ? 'bg-amber-50/80 border border-amber-200 text-amber-950'
                          : 'bg-surface-warm border border-surface-border text-ink'
                        : 'bg-lime-600 text-white'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.content}</p>
                    {isAssistant && (
                      <button
                        onClick={() => speakWithMicSuppression(m.content)}
                        className="mt-2 text-xs text-ink-muted hover:text-ink flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity"
                        title="Listen to question"
                      >
                        <Volume2 className="w-3.5 h-3.5" />
                        <span>Listen</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {isSending && (
              <div className="flex flex-col items-start">
                <span className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider mb-1 px-1">
                  Interviewer
                </span>
                <div className="bg-surface-warm border border-surface-border rounded-2xl p-3.5 text-xs text-ink-muted flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-lime-600 animate-pulse" />
                  Analyzing response against rubric dimensions...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Active Voice Input Wave Banner */}
          {isListening && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-900 text-xs flex items-center justify-between animate-fade-in shadow-xs">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping" />
                <span className="font-semibold">
                  Listening to your answer... Speak naturally into your microphone.
                </span>
              </div>
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={toggleSpeechRecognition}
                className="text-xs py-1 px-2.5"
              >
                Done Speaking
              </Button>
            </div>
          )}

          {/* Input Box & Speech Controls */}
          <form onSubmit={handleSendMessage} className="space-y-2">
            <div className="relative rounded-xl border border-surface-border bg-white shadow-xs focus-within:ring-2 focus-within:ring-lime-500 overflow-hidden">
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => {
                  setInputText(e.target.value);
                  baseInputTextRef.current = e.target.value;
                }}
                placeholder="State your technical answer directly. Cite metrics or trade-offs (Press Enter to submit, or use mic below)..."
                className="w-full p-3.5 text-xs sm:text-sm text-ink placeholder:text-ink-faint focus:outline-none resize-none font-sans"
                disabled={isSending}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />

              <div className="flex items-center justify-between px-3 py-2 bg-surface-warm border-t border-surface-border">
                <div className="flex items-center gap-2">
                  {isSpeechSupported && (
                    <Button
                      type="button"
                      variant={isListening ? 'danger' : 'secondary'}
                      size="sm"
                      onClick={toggleSpeechRecognition}
                      title={isListening ? 'Stop microphone' : 'Push to speak answer'}
                      className="gap-1.5 text-xs font-medium"
                    >
                      {isListening ? (
                        <>
                          <MicOff className="w-3.5 h-3.5 animate-pulse" />
                          <span>Stop Listening</span>
                        </>
                      ) : (
                        <>
                          <Mic className="w-3.5 h-3.5 text-lime-700" />
                          <span>Speak Answer</span>
                        </>
                      )}
                    </Button>
                  )}
                  <span className="text-[11px] text-ink-subtle hidden sm:inline">
                    Enter to send · Shift+Enter for newline
                  </span>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isSending}
                  disabled={!inputText.trim()}
                  className="gap-1.5 text-xs font-semibold px-4"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send Answer</span>
                </Button>
              </div>
            </div>
          </form>
        </div>

        {/* Right Column: Docked Coding Panel (Monaco Editor) */}
        {showCodeEditor && (
          <div className="lg:col-span-6 space-y-3 flex flex-col">
            <Card className="p-3.5 bg-white border border-surface-border space-y-3 flex-1 flex flex-col">
              <div className="flex items-center justify-between pb-2.5 border-b border-surface-border">
                <div className="flex items-center gap-1.5">
                  {(['python', 'java', 'cpp'] as const).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => handleLanguageChange(lang)}
                      className={`px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors ${
                        codeLanguage === lang
                          ? 'bg-lime-100 text-lime-900 border border-lime-300 font-semibold'
                          : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                      }`}
                    >
                      {lang === 'python' ? 'Python' : lang === 'java' ? 'Java' : 'C++'}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      if (codingProblem) {
                        setCode(codingProblem.starter_code[codeLanguage] || '');
                      }
                    }}
                    title="Reset starter code"
                    className="text-xs"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleRunCode}
                    isLoading={isExecutingCode}
                    className="gap-1.5 text-xs font-medium"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Run Code</span>
                  </Button>
                </div>
              </div>

              {/* Monaco Code Editor */}
              <div className="h-80 border border-surface-border rounded-lg overflow-hidden">
                <Editor
                  height="100%"
                  language={
                    codeLanguage === 'cpp'
                      ? 'cpp'
                      : codeLanguage === 'java'
                      ? 'java'
                      : 'python'
                  }
                  theme="vs"
                  value={code}
                  onChange={(val) => setCode(val || '')}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 12,
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    tabSize: 4,
                    automaticLayout: true,
                  }}
                />
              </div>

              {/* Execution Output */}
              {executionResult && (
                <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border font-mono text-[11px] space-y-1.5 max-h-36 overflow-y-auto">
                  <div className="flex items-center justify-between font-sans">
                    <span className="font-semibold text-xs flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5 text-lime-600" />
                      Sandbox Results
                    </span>
                    <Badge
                      variant={executionResult.status === 'passed' ? 'emerald' : 'rose'}
                      className="text-[9px] uppercase font-mono"
                    >
                      {executionResult.status} ({executionResult.execution_time_ms}ms)
                    </Badge>
                  </div>
                  <div className="text-ink-muted">
                    Passed {executionResult.total_passed} / {executionResult.total_tests} test cases
                  </div>
                  {executionResult.stderr && (
                    <div className="text-rose-600 whitespace-pre-wrap">
                      {executionResult.stderr}
                    </div>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* Exit Confirmation Modal */}
      <Modal
        isOpen={showExitConfirmModal}
        onClose={() => setShowExitConfirmModal(false)}
        title="Exit Active Interview Session?"
      >
        <div className="space-y-4 text-xs">
          <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              Are you sure you want to leave? Your conversation history and code drafts are preserved, but leaving the focus room interrupts the live interview flow.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-surface-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowExitConfirmModal(false)}
            >
              Cancel (Stay in Interview)
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={() => navigate('/')}
            >
              Exit to Dashboard
            </Button>
          </div>
        </div>
      </Modal>

      {/* Self Evaluation Modal */}
      {interview && (
        <SelfEvaluationModal
          isOpen={showSelfEvalModal}
          onClose={() => setShowSelfEvalModal(false)}
          interviewId={interview.id}
          category={interview.category}
          rubrics={rubrics}
          onComplete={() => navigate(`/evaluations/${interview.id}`)}
        />
      )}
    </div>
  );
};
