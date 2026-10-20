import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../../lib/api';
import { Interview, InterviewMessage, RubricDimension, CodeExecutionResult, CodingProblem, HintResponse } from '../../lib/types';
import { SpeechHandler } from '../../lib/speech';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { AudioWaveform } from '../../components/ui/AudioWaveform';
import { SelfEvaluationModal } from './SelfEvaluationModal';
import {
  Code2,
  Lightbulb,
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

  // Elapsed Timer
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const baseInputTextRef = useRef<string>('');
  const codeDraftsRef = useRef<Record<string, string>>({});

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
      .then(setRubrics)
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

  const speakWithMicSuppression = useCallback((text: string) => {
    if (!speechHandlerRef.current) return;
    if (isListening) {
      speechHandlerRef.current.stop();
    }
    setIsSpeaking(true);
    SpeechHandler.speak(text, () => {
      setIsSpeaking(false);
    });
  }, [isListening]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const content = inputText.trim();
    if (!content || !id || isSending) return;

    if (isListening) {
      speechHandlerRef.current?.stop();
    }

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
    setInputText('');
    baseInputTextRef.current = '';
    setIsSending(true);

    try {
      const assistantMsg = await api.post<InterviewMessage>(`/interviews/${id}/message`, {
        content,
      });
      setMessages((prev) => [...prev.filter((m) => m.id !== optimisticMsg.id), optimisticMsg, assistantMsg]);

      if (autoSpeak) {
        speakWithMicSuppression(assistantMsg.content);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send message.');
    } finally {
      setIsSending(false);
    }
  };

  const handleRequestHint = async (level: number) => {
    if (!id || isRequestingHint) return;
    setIsRequestingHint(true);
    setShowHintMenu(false);

    try {
      const res = await api.post<HintResponse>(`/interviews/${id}/hint`, {
        level,
        problem_id: codingProblem?.id,
        current_code: code || undefined,
      });

      setHintLevelUsed(res.total_hint_level_used);

      // Refresh interview messages to reflect candidate request and assistant hint
      const updated = await api.get<Interview>(`/interviews/${id}`);
      setMessages(updated.messages || []);

      if (autoSpeak) {
        speakWithMicSuppression(res.hint);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to request Socratic hint.');
    } finally {
      setIsRequestingHint(false);
    }
  };

  const toggleSpeechRecognition = () => {
    if (!speechHandlerRef.current) return;
    if (isListening) {
      speechHandlerRef.current.stop();
    } else {
      SpeechHandler.stopSpeaking();
      baseInputTextRef.current = inputText;
      speechHandlerRef.current.start();
    }
  };

  const handleRunCode = async () => {
    if (!codingProblem) return;
    setIsExecutingCode(true);
    setExecutionResult(null);

    try {
      const result = await api.post<CodeExecutionResult>('/coding/run', {
        problem_id: codingProblem.id,
        language: codeLanguage,
        code,
      });
      setExecutionResult(result);
    } catch (err: any) {
      alert(err.message || 'Code execution failed');
    } finally {
      setIsExecutingCode(false);
    }
  };

  const handleLanguageChange = (lang: 'python' | 'java' | 'cpp') => {
    codeDraftsRef.current[codeLanguage] = code;
    setCodeLanguage(lang);
    const draft = codeDraftsRef.current[lang];
    setCode(draft !== undefined ? draft : (codingProblem?.starter_code[lang] || ''));
  };

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const assistantCount = messages.filter((m) => m.role === 'assistant').length;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-ink-muted">Connecting to interview room...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-4">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3.5 border-b border-surface-border gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold tracking-tight text-ink">{interview?.title}</h1>
            <Badge variant="lime" size="sm" className="font-mono text-[10px] uppercase">
              {interview?.category}
            </Badge>
            <span className="text-xs text-ink-subtle">
              Question <strong>{Math.min(8, assistantCount)}</strong> of ~8
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-ink-muted mt-0.5">
            <span>Role: {interview?.target_role}</span>
            <span>•</span>
            <span className="capitalize">Level: {interview?.difficulty}</span>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Audio Waveform Presence */}
          <AudioWaveform
            isActive={isSpeaking || isListening}
            label={isSpeaking ? 'Interviewer Speaking' : isListening ? 'Listening (Mic Active)' : 'Interviewer Ready'}
          />

          {/* Elapsed Timer */}
          <div className="font-mono text-xs font-semibold bg-surface-subtle px-3 py-1.5 rounded-lg border border-surface-border text-ink">
            {formatTime(secondsElapsed)} / {interview?.target_duration_minutes || 20}:00
          </div>

          {/* AI Voice Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setAutoSpeak(!autoSpeak)}
            title={autoSpeak ? 'Mute AI Voice' : 'Enable AI Voice readout'}
            className="text-xs gap-1"
          >
            {autoSpeak ? <Volume2 className="w-4 h-4 text-lime-700" /> : <VolumeX className="w-4 h-4 text-ink-subtle" />}
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
            {showCodeEditor ? 'Hide Code' : 'Dock Code'}
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
                    <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono">-5%</span>
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
                    <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-mono">-15%</span>
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
                    <span className="text-[10px] text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded font-mono">-30%</span>
                  </div>
                  <div className="text-[11px] text-ink-muted">Step-by-step structural logic walkthrough.</div>
                </button>
              </div>
            )}
          </div>

          {/* End & Self-Evaluate Button */}
          <Button
            variant="danger"
            size="sm"
            onClick={() => setShowSelfEvalModal(true)}
            className="text-xs font-semibold"
          >
            End & Self-Evaluate
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
          {error}
        </div>
      )}

      {/* Main Split Layout: Dialogue & Code Sandbox */}
      <div className={`grid gap-5 ${showCodeEditor ? 'grid-cols-1 lg:grid-cols-12' : 'grid-cols-1 max-w-4xl mx-auto'}`}>
        {/* Left Column: Conversational Dialogue */}
        <div className={showCodeEditor ? 'lg:col-span-6 space-y-3' : 'space-y-3'}>
          <div className="bg-white border border-surface-border rounded-xl p-4 sm:p-5 shadow-card min-h-[480px] max-h-[580px] overflow-y-auto space-y-4">
            {messages.map((m, idx) => {
              const isAssistant = m.role === 'assistant';
              const isHintMsg = m.content.startsWith('[Level') || m.content.startsWith('[Requested Level');

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
                    className={`max-w-[88%] rounded-2xl p-4 text-sm leading-relaxed shadow-sm ${
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
                        Listen
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

          {/* Input Box */}
          <form onSubmit={handleSendMessage} className="space-y-2">
            <div className="relative rounded-xl border border-surface-border bg-white shadow-card focus-within:ring-2 focus-within:ring-lime-500 overflow-hidden">
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => {
                  setInputText(e.target.value);
                  baseInputTextRef.current = e.target.value;
                }}
                placeholder="State your technical answer directly. Cite numbers or trade-offs (Press Enter to submit, Space to speak)..."
                className="w-full p-3.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none resize-none font-sans"
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
                      title={isListening ? 'Stop listening' : 'Push to talk (or hold Space)'}
                      className="gap-1.5 text-xs"
                    >
                      {isListening ? (
                        <>
                          <MicOff className="w-3.5 h-3.5 animate-pulse" />
                          <span>Stop Mic</span>
                        </>
                      ) : (
                        <>
                          <Mic className="w-3.5 h-3.5 text-lime-700" />
                          <span>Voice Input</span>
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
                  className="gap-1.5 text-xs font-semibold"
                >
                  <Send className="w-3.5 h-3.5" />
                  Respond
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
                    Test Code
                  </Button>
                </div>
              </div>

              {/* Monaco Code Editor */}
              <div className="h-80 border border-surface-border rounded-lg overflow-hidden">
                <Editor
                  height="100%"
                  language={codeLanguage === 'cpp' ? 'cpp' : codeLanguage === 'java' ? 'java' : 'python'}
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
                    <div className="text-rose-600 whitespace-pre-wrap">{executionResult.stderr}</div>
                  )}
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

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
