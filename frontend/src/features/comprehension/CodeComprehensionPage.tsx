import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Brain, CheckCircle2, Clock, FileCode2, Flag, Play, XCircle, AlertCircle, ChevronRight } from 'lucide-react';
import { api } from '../../lib/api';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

interface ItemSummary {
  id: string;
  title: string;
  difficulty: string;
  tags: string[];
  context: string;
  estimated_minutes: number;
  question_count: number;
}
interface Question {
  id: string;
  type: string;
  prompt: string;
}
interface AnswerState {
  answer?: string;
  follow_up?: string | null;
  follow_up_answer?: string;
  score?: number;
  verdict?: string;
  feedback?: string;
  location_correct?: boolean | null;
  done?: boolean;
}
interface Session {
  id: string;
  status: 'in_progress' | 'completed';
  score: number | null;
  time_limit_minutes: number;
  started_at: string;
  item: ItemSummary & { files: Record<string, string>; questions: Question[] };
  answers: Record<string, AnswerState>;
  reveal?: {
    bug_lines: { file: string; line: number }[];
    questions: Record<string, { key_points: string[]; expected_output: string | null }>;
  };
}
interface HistoryRow {
  id: string;
  title: string;
  status: string;
  score: number | null;
  started_at: string;
}

const TYPE_LABEL: Record<string, string> = {
  explain: 'Explain',
  trace: 'Trace the output',
  bug: 'Find the bug',
  review: 'Review',
  numeric: 'Estimate',
};

const verdictStyle = (v?: string) =>
  v === 'correct'
    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
    : v === 'partial'
    ? 'bg-amber-50 border-amber-200 text-amber-900'
    : 'bg-rose-50 border-rose-200 text-rose-900';

/* ----------------------------------------------------------------------------- catalog */

const Catalog: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [starting, setStarting] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<ItemSummary[]>('/comprehension/items').then(setItems).catch((e) => setError(e.message));
    api.get<HistoryRow[]>('/comprehension/history').then(setHistory).catch(() => {});
  }, []);

  const start = async (id: string) => {
    setStarting(id);
    try {
      const s = await api.post<Session>('/comprehension/sessions', { item_id: id });
      navigate(`/comprehension/${s.id}`);
    } catch (e: any) {
      setError(e.message);
      setStarting(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      <header className="space-y-2">
        <Badge variant="lime" size="sm" className="font-mono uppercase tracking-wider">New · Code comprehension</Badge>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Read code you didn't write.</h1>
        <p className="text-slate-600 max-w-2xl">
          The round big-tech interviews actually test: real infrastructure code, planted production bugs. Explain it, trace
          it exactly, find the line that breaks, and write the review comment. Graded against a hidden answer key.
        </p>
      </header>
      {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-sm">{error}</div>}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((it, idx) => (
          <div
            key={it.id}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-xs hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 flex flex-col"
            style={{ animationDelay: `${idx * 40}ms` }}
          >
            <div className="flex items-center justify-between gap-2">
              <FileCode2 className="w-5 h-5 text-slate-400 group-hover:text-lime-600 transition-colors" />
              <Badge variant={it.difficulty === 'hard' ? 'rose' : 'amber'} size="sm" className="uppercase font-mono">
                {it.difficulty}
              </Badge>
            </div>
            <h3 className="mt-3 font-semibold text-slate-900">{it.title}</h3>
            <p className="mt-1 text-sm text-slate-600 flex-1">{it.context}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {it.tags.map((t) => (
                <span key={t} className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">{t}</span>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
              <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{it.estimated_minutes} min · {it.question_count} questions</span>
              <Button size="sm" variant="primary" isLoading={starting === it.id} onClick={() => start(it.id)} className="gap-1">
                <Play className="w-3.5 h-3.5" /> Start
              </Button>
            </div>
          </div>
        ))}
      </div>

      {history.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Your attempts</h2>
          <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100">
            {history.slice(0, 8).map((h) => (
              <button
                key={h.id}
                onClick={() => navigate(`/comprehension/${h.id}`)}
                className="w-full px-4 py-2.5 flex items-center justify-between text-sm hover:bg-slate-50 text-left"
              >
                <span className="font-medium text-slate-800">{h.title}</span>
                <span className="flex items-center gap-3 text-slate-500">
                  {h.status === 'completed' ? `${Math.round(h.score ?? 0)}/100` : 'in progress'}
                  <ChevronRight className="w-4 h-4" />
                </span>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

/* ----------------------------------------------------------------------------- session */

const CodeViewer: React.FC<{
  files: Record<string, string>;
  onLineClick: (file: string, line: number) => void;
  bugLines: { file: string; line: number }[];
}> = ({ files, onLineClick, bugLines }) => {
  const names = Object.keys(files);
  const [active, setActive] = useState(names[0]);
  const lines = (files[active] || '').replace(/\n$/, '').split('\n');
  const isBug = (n: number) => bugLines.some((b) => b.file === active && b.line === n);
  return (
    <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-xs">
      <div className="flex items-center gap-1 px-2 pt-2 bg-slate-50 border-b border-slate-200">
        {names.map((n) => (
          <button
            key={n}
            onClick={() => setActive(n)}
            className={`px-3 py-1.5 text-xs font-mono rounded-t-md ${n === active ? 'bg-white border border-b-white border-slate-200 text-slate-900' : 'text-slate-500 hover:text-slate-800'}`}
          >
            {n}
          </button>
        ))}
        <span className="ml-auto text-[11px] text-slate-400 pr-2">Click a line number to reference it</span>
      </div>
      <pre className="text-[13px] leading-6 font-mono overflow-auto max-h-[70vh] [font-variant-ligatures:none]">
        {lines.map((l, i) => (
          <div key={i} className={`flex ${isBug(i + 1) ? 'bg-rose-50' : 'hover:bg-lime-50/60'}`}>
            <button
              onClick={() => onLineClick(active, i + 1)}
              className={`w-12 shrink-0 text-right pr-3 select-none ${isBug(i + 1) ? 'text-rose-600 font-bold' : 'text-slate-400 hover:text-lime-700'}`}
              aria-label={`Reference line ${i + 1}`}
            >
              {i + 1}
            </button>
            <code className="whitespace-pre pr-4 text-slate-800">{l || ' '}</code>
          </div>
        ))}
      </pre>
    </div>
  );
};

const SessionView: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [activeQ, setActiveQ] = useState<string>('');
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [now, setNow] = useState(Date.now());
  const textareas = useRef<Record<string, HTMLTextAreaElement | null>>({});

  const load = useCallback(() => {
    api.get<Session>(`/comprehension/sessions/${sessionId}`)
      .then((s) => {
        setSession(s);
        setActiveQ((prev) => prev || s.item.questions[0]?.id || '');
      })
      .catch((e) => setError(e.message));
  }, [sessionId]);

  useEffect(load, [load]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const remaining = useMemo(() => {
    if (!session) return 0;
    const end = Date.parse(session.started_at) + session.time_limit_minutes * 60000;
    return Math.max(0, Math.floor((end - now) / 1000));
  }, [session, now]);

  if (error && !session) return <div className="max-w-3xl mx-auto p-8 text-rose-700">{error}</div>;
  if (!session) return <div className="max-w-7xl mx-auto p-8"><div className="h-96 rounded-2xl bg-slate-100 animate-pulse" /></div>;

  const done = session.status === 'completed';
  const answered = session.item.questions.filter((q) => session.answers[q.id]?.done).length;

  const insertLine = (_file: string, line: number) => {
    if (done || !activeQ) return;
    setDrafts((d) => ({ ...d, [activeQ]: `${(d[activeQ] || '').trimEnd()}${d[activeQ] ? ' ' : ''}L${line} ` }));
    textareas.current[activeQ]?.focus();
  };

  const submit = async (q: Question) => {
    const text = (drafts[q.id] || '').trim();
    if (!text) return;
    setBusy(q.id);
    setError('');
    try {
      await api.post(`/comprehension/sessions/${session.id}/answer`, { question_id: q.id, answer: text });
      setDrafts((d) => ({ ...d, [q.id]: '' }));
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const finish = async () => {
    setBusy('finish');
    try {
      setSession(await api.post<Session>(`/comprehension/sessions/${session.id}/finish`));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
  const ss = String(remaining % 60).padStart(2, '0');

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-5 space-y-4 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-xs">
        <div className="flex items-center gap-3">
          <Brain className="w-5 h-5 text-lime-600" />
          <div>
            <h1 className="text-sm font-bold text-slate-900">{session.item.title}</h1>
            <p className="text-xs text-slate-500">{session.item.context}</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="text-xs text-slate-500">{answered}/{session.item.questions.length} answered</span>
          {!done && (
            <span className={`font-mono text-xs font-semibold px-2.5 py-1 rounded-md border ${remaining < 120 ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-slate-200 bg-slate-50 text-slate-800'}`}>
              ⏱ {mm}:{ss}
            </span>
          )}
          {done ? (
            <Badge variant="lime" size="md" className="font-mono">{Math.round(session.score ?? 0)}/100</Badge>
          ) : (
            <Button size="sm" variant="primary" onClick={finish} isLoading={busy === 'finish'} className="gap-1">
              <Flag className="w-3.5 h-3.5" /> Finish & reveal
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => navigate('/comprehension')}>All items</Button>
        </div>
      </div>

      {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-sm">{error}</div>}

      <div className="grid lg:grid-cols-[1.15fr_1fr] gap-4 items-start">
        <div className="lg:sticky lg:top-4">
          <CodeViewer files={session.item.files} onLineClick={insertLine} bugLines={done ? session.reveal?.bug_lines || [] : []} />
        </div>

        <div className="space-y-3">
          {session.item.questions.map((q, idx) => {
            const a = session.answers[q.id] || {};
            const awaitingFollowUp = !!a.follow_up && !a.done;
            const locked = done || a.done;
            const rev = session.reveal?.questions[q.id];
            return (
              <div
                key={q.id}
                onClick={() => setActiveQ(q.id)}
                className={`rounded-2xl border bg-white p-4 shadow-xs transition-all ${activeQ === q.id && !locked ? 'border-lime-400 ring-2 ring-lime-200' : 'border-slate-200'}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500">
                    {idx + 1}. {TYPE_LABEL[q.type] || q.type}
                  </span>
                  {a.verdict && (
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border flex items-center gap-1 ${verdictStyle(a.verdict)}`}>
                      {a.verdict === 'correct' ? <CheckCircle2 className="w-3 h-3" /> : a.verdict === 'partial' ? <AlertCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      {a.verdict} · {Math.round((a.score ?? 0) * 100)}%
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm font-medium text-slate-900">{q.prompt}</p>

                {a.answer && (
                  <div className="mt-3 text-sm text-slate-700 bg-slate-50 rounded-lg p-3 whitespace-pre-wrap">{a.answer}</div>
                )}
                {a.feedback && <p className="mt-2 text-xs text-slate-600">{a.feedback}</p>}
                {a.follow_up && (
                  <div className="mt-3 text-sm border-l-2 border-lime-500 pl-3 text-slate-800">
                    <span className="text-[11px] uppercase tracking-wider text-lime-700 font-semibold">Reviewer follow-up</span>
                    <p>{a.follow_up}</p>
                    {a.follow_up_answer && <p className="mt-1 text-slate-600 whitespace-pre-wrap">{a.follow_up_answer}</p>}
                  </div>
                )}

                {!locked && (
                  <div className="mt-3 space-y-2">
                    <textarea
                      ref={(el) => (textareas.current[q.id] = el)}
                      rows={q.type === 'trace' ? 4 : 3}
                      value={drafts[q.id] || ''}
                      onFocus={() => setActiveQ(q.id)}
                      onChange={(e) => setDrafts((d) => ({ ...d, [q.id]: e.target.value }))}
                      placeholder={
                        awaitingFollowUp
                          ? 'Answer the reviewer…'
                          : q.type === 'trace'
                          ? 'Exact output, one line per print'
                          : q.type === 'bug'
                          ? 'Reference the line (click a line number, e.g. L12) and explain why it breaks'
                          : 'Your answer'
                      }
                      className={`w-full p-3 text-sm border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-300 ${q.type === 'trace' ? 'font-mono' : ''}`}
                    />
                    <div className="flex justify-end">
                      <Button size="sm" variant="primary" isLoading={busy === q.id} disabled={!(drafts[q.id] || '').trim()} onClick={() => submit(q)}>
                        {awaitingFollowUp ? 'Answer follow-up' : 'Submit'}
                      </Button>
                    </div>
                  </div>
                )}

                {done && rev && (
                  <div className="mt-3 rounded-lg bg-lime-50/70 border border-lime-200 p-3 text-xs text-slate-800 space-y-1">
                    <span className="font-semibold uppercase tracking-wider text-lime-800">Answer key</span>
                    {rev.expected_output && <pre className="font-mono bg-white border border-lime-200 rounded p-2 whitespace-pre-wrap">{rev.expected_output}</pre>}
                    {rev.key_points.length > 0 && (
                      <ul className="list-disc pl-4 space-y-0.5">
                        {rev.key_points.map((k) => <li key={k}>{k}</li>)}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export const CodeComprehensionPage: React.FC = () => {
  const { sessionId } = useParams();
  return sessionId ? <SessionView sessionId={sessionId} /> : <Catalog />;
};
