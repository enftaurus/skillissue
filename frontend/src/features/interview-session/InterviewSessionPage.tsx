import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../lib/api';
import { Interview, InterviewMessage, RubricDimension, CodeExecutionResult, CodingProblem } from '../../lib/types';
import { SpeechHandler } from '../../lib/speech';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { SelfEvaluationModal } from './SelfEvaluationModal';
import {
  CheckCircle2,
  Code2,
  Mic,
  MicOff,
  Play,
  Send,
  Volume2,
  VolumeX,
  XCircle,
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
  const speechHandlerRef = useRef<SpeechHandler | null>(null);

  // Coding Sandbox Pane (for DSA category)
  const [showCodeEditor, setShowCodeEditor] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState<'python' | 'java' | 'cpp'>('python');
  const [code, setCode] = useState('');
  const [codingProblem, setCodingProblem] = useState<CodingProblem | null>(null);
  const [executionResult, setExecutionResult] = useState<CodeExecutionResult | null>(null);
  const [isExecutingCode, setIsExecutingCode] = useState(false);

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
        if (data.category === 'dsa') {
          setShowCodeEditor(true);
          // Load default problem (two-sum)
          api.get<CodingProblem>('/coding/problems/two-sum')
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

    // Initialize Speech Handler with non-duplicating committed/interim handling
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

  // 2. Timer Interval
  useEffect(() => {
    if (interview?.status === 'in_progress') {
      const interval = setInterval(() => {
        setSecondsElapsed((s) => s + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [interview?.status]);

  // 3. Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  // Speech & TTS coordination: temporarily pause microphone while TTS audio is playing
  const speakWithMicSuppression = (text: string) => {
    const wasListening = isListening;
    if (wasListening && speechHandlerRef.current) {
      speechHandlerRef.current.stop();
    }
    SpeechHandler.speak(text, () => {
      if (wasListening && speechHandlerRef.current) {
        speechHandlerRef.current.start();
      }
    });
  };

  // 4. Handle Send Message
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isSending || !id) return;

    const content = inputText.trim();
    baseInputTextRef.current = '';
    setInputText('');
    setIsSending(true);
    setError('');

    if (speechHandlerRef.current) {
      speechHandlerRef.current.stop();
    }

    // Optimistically append user message
    const tempUserMsg: InterviewMessage = {
      id: `temp-${Date.now()}`,
      interview_id: id,
      role: 'user',
      content,
      question_index: messages.length + 1,
      is_follow_up: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const assistantMsg = await api.post<InterviewMessage>(`/interviews/${id}/message`, {
        content,
      });
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg]);

      // If auto-speak enabled, read out the assistant question safely
      if (autoSpeak) {
        speakWithMicSuppression(assistantMsg.content);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to receive interview response.');
    } finally {
      setIsSending(false);
    }
  };

  const toggleMic = () => {
    if (!speechHandlerRef.current) return;
    if (isListening) {
      speechHandlerRef.current.stop();
    } else {
      baseInputTextRef.current = inputText.trim();
      speechHandlerRef.current.start();
    }
  };

  const handleRunCodeInSandbox = async () => {
    if (!code.trim() || !codingProblem) return;
    setIsExecutingCode(true);
    try {
      const res = await api.post<CodeExecutionResult>('/coding/run', {
        problem_id: codingProblem.id,
        language: codeLanguage,
        code,
      });
      setExecutionResult(res);
    } catch (err: any) {
      setError(err.message || 'Sandbox execution error.');
    } finally {
      setIsExecutingCode(false);
    }
  };

  const handleLanguageChange = (newLang: 'python' | 'java' | 'cpp') => {
    // Preserve current language code draft
    codeDraftsRef.current[codeLanguage] = code;
    setCodeLanguage(newLang);

    // Restore existing draft for new language, or fall back to starter code
    const existingDraft = codeDraftsRef.current[newLang];
    if (existingDraft !== undefined) {
      setCode(existingDraft);
    } else if (codingProblem && codingProblem.starter_code[newLang]) {
      const starter = codingProblem.starter_code[newLang];
      codeDraftsRef.current[newLang] = starter;
      setCode(starter);
    }
  };

  const handleEndInterviewClick = () => {
    setShowSelfEvalModal(true);
  };

  const handleEvaluationComplete = () => {
    setShowSelfEvalModal(false);
    navigate(`/evaluations/${id}`);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="inline-block animate-spin w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full" />
        <p className="mt-3 text-sm text-ink-muted">Setting up live interview chamber...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 space-y-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-surface-border gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-ink">{interview?.title}</h1>
            <Badge variant="lime" size="sm">
              {interview?.category.toUpperCase()}
            </Badge>
          </div>
          <p className="text-xs text-ink-subtle mt-0.5">
            Role: {interview?.target_role} · Difficulty: {interview?.difficulty}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="font-mono text-sm font-semibold bg-surface-subtle px-3 py-1.5 rounded-md border border-surface-border text-ink">
            {formatTime(secondsElapsed)} / {interview?.target_duration_minutes}:00
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setAutoSpeak(!autoSpeak)}
            title={autoSpeak ? 'Mute AI Voice' : 'Enable AI Voice readout'}
          >
            {autoSpeak ? <Volume2 className="w-4 h-4 text-lime-700" /> : <VolumeX className="w-4 h-4 text-ink-subtle" />}
          </Button>

          {interview?.category === 'dsa' && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCodeEditor(!showCodeEditor)}
            >
              <Code2 className="w-4 h-4 mr-1 text-lime-700" />
              {showCodeEditor ? 'Hide Editor' : 'Code Editor'}
            </Button>
          )}

          <Button
            variant="danger"
            size="sm"
            onClick={handleEndInterviewClick}
          >
            End & Self-Evaluate
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-md">
          {error}
        </div>
      )}

      {/* Main View: Transcript & (optional) Sandbox Editor */}
      <div className={`grid gap-6 ${showCodeEditor ? 'grid-cols-1 lg:grid-cols-12' : 'grid-cols-1 max-w-4xl mx-auto'}`}>
        {/* Left Column: Conversational Transcript */}
        <div className={showCodeEditor ? 'lg:col-span-6 space-y-4' : 'space-y-4'}>
          <div className="bg-white border border-surface-border rounded-xl p-4 sm:p-6 shadow-card min-h-[460px] max-h-[580px] overflow-y-auto space-y-4">
            {messages.map((m, idx) => {
              const isAssistant = m.role === 'assistant';
              return (
                <div
                  key={m.id || idx}
                  className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'}`}
                >
                  <span className="text-[10px] font-semibold text-ink-subtle uppercase tracking-wider mb-1 px-1">
                    {isAssistant ? 'Interviewer' : 'You'}
                  </span>
                  <div
                    className={`max-w-[88%] rounded-2xl p-4 text-sm leading-relaxed shadow-sm ${
                      isAssistant
                        ? 'bg-surface-warm border border-surface-border text-ink'
                        : 'bg-lime-600 text-white'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{m.content}</p>
                    {isAssistant && (
                      <button
                        onClick={() => speakWithMicSuppression(m.content)}
                        className="mt-2 text-xs text-ink-muted hover:text-ink flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity"
                        title="Listen to question"
                        aria-label="Listen to question audio"
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
                <div className="bg-surface-warm border border-surface-border rounded-2xl p-4 text-sm text-ink-muted flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-lime-600 animate-pulse" />
                  Formulating next probing question...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Answer Input Box */}
          <form onSubmit={handleSendMessage} className="space-y-2">
            <div className="relative rounded-xl border border-surface-border bg-white shadow-card focus-within:ring-2 focus-within:ring-lime-500 overflow-hidden">
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => {
                  setInputText(e.target.value);
                  baseInputTextRef.current = e.target.value;
                }}
                placeholder="Type your direct explanation, or click mic to speak..."
                className="w-full p-3 text-sm text-ink placeholder:text-ink-faint focus:outline-none resize-none"
                disabled={isSending}
                aria-label="Your interview response"
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
                    <button
                      type="button"
                      onClick={toggleMic}
                      className={`p-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                        isListening
                          ? 'bg-red-500 text-white animate-pulse'
                          : 'text-ink-muted hover:text-ink hover:bg-surface-subtle'
                      }`}
                      title={isListening ? 'Stop listening' : 'Start voice input'}
                      aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
                    >
                      {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                      <span className="text-xs">{isListening ? 'Listening...' : 'Voice Input'}</span>
                    </button>
                  )}
                  <span className="text-[11px] text-ink-subtle hidden sm:inline">
                    Press Enter to send (Shift+Enter for newline)
                  </span>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!inputText.trim() || isSending}
                  isLoading={isSending}
                >
                  <Send className="w-3.5 h-3.5 mr-1" />
                  Send Answer
                </Button>
              </div>
            </div>
          </form>
        </div>

        {/* Right Column: Code Editor & Sandbox (for DSA rounds) */}
        {showCodeEditor && (
          <div className="lg:col-span-6 space-y-4">
            <Card className="p-4 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-border">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-lime-700" />
                  <span className="font-semibold text-sm text-ink">
                    {codingProblem?.title || 'Coding Sandbox'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={codeLanguage}
                    onChange={(e) => handleLanguageChange(e.target.value as any)}
                    aria-label="Code language"
                    className="text-xs font-medium px-2 py-1 bg-surface-subtle border border-surface-border rounded text-ink focus:outline-none"
                  >
                    <option value="python">Python 3</option>
                    <option value="cpp">C++ 17</option>
                    <option value="java">Java 21</option>
                  </select>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleRunCodeInSandbox}
                    isLoading={isExecutingCode}
                  >
                    <Play className="w-3 h-3 mr-1 fill-white" />
                    Run in Sandbox
                  </Button>
                </div>
              </div>

              {codingProblem && (
                <div className="text-xs text-ink-muted bg-surface-warm p-3 rounded-md border border-surface-border space-y-1">
                  <p className="font-medium text-ink">{codingProblem.description}</p>
                  <p className="text-ink-subtle">Target Constraints: {codingProblem.constraints.join(' · ')}</p>
                </div>
              )}

              {/* In-Browser Code Area */}
              <div className="rounded-lg border border-surface-border overflow-hidden bg-zinc-950 font-mono text-xs">
                <textarea
                  rows={14}
                  value={code}
                  onChange={(e) => {
                    const val = e.target.value;
                    setCode(val);
                    codeDraftsRef.current[codeLanguage] = val;
                  }}
                  aria-label="Code editor"
                  className="w-full p-4 bg-transparent text-emerald-300 placeholder:text-zinc-600 focus:outline-none resize-none leading-relaxed"
                  spellCheck={false}
                />
              </div>

              {/* Sandbox Execution Results Output */}
              {executionResult && (
                <div className="p-3 bg-surface-warm rounded-lg border border-surface-border space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-ink flex items-center gap-1.5">
                      Execution Result:
                      {executionResult.status === 'passed' ? (
                        <span className="text-lime-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> All Tests Passed ({executionResult.total_passed}/{executionResult.total_tests})
                        </span>
                      ) : (
                        <span className="text-red-600 flex items-center gap-1">
                          <XCircle className="w-3.5 h-3.5" /> {executionResult.status.toUpperCase()} ({executionResult.total_passed}/{executionResult.total_tests})
                        </span>
                      )}
                    </span>
                    <span className="font-mono text-ink-subtle">{executionResult.execution_time_ms}ms</span>
                  </div>

                  {executionResult.stderr && (
                    <pre className="p-2 bg-red-50 text-red-800 rounded text-[11px] font-mono overflow-x-auto whitespace-pre-wrap">
                      {executionResult.stderr}
                    </pre>
                  )}

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    {executionResult.test_results.map((tr) => (
                      <div
                        key={tr.test_index}
                        className={`p-2 rounded border text-[11px] ${
                          tr.passed
                            ? 'bg-lime-50/60 border-lime-200 text-lime-900'
                            : 'bg-red-50/60 border-red-200 text-red-900'
                        }`}
                      >
                        <div className="flex justify-between font-semibold">
                          <span>Test #{tr.test_index}</span>
                          <span>{tr.passed ? 'PASS' : 'FAIL'}</span>
                        </div>
                        {!tr.is_hidden && (
                          <div className="mt-1 font-mono text-[10px] text-ink-subtle truncate">
                            Out: {tr.actual_stdout}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>

      {/* Candidate Self-Evaluation Modal */}
      {interview && (
        <SelfEvaluationModal
          isOpen={showSelfEvalModal}
          onClose={() => setShowSelfEvalModal(false)}
          interviewId={interview.id}
          category={interview.category}
          rubrics={rubrics}
          onComplete={handleEvaluationComplete}
        />
      )}
    </div>
  );
};
