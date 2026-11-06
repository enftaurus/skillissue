import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import {
  AlertTriangle, ArrowRight, Boxes, Brain, Building2, CheckCircle2, Clock, Code2, FileText, Lock, Mic, Play,
  Send, ShieldAlert, ShieldCheck, XCircle,
} from 'lucide-react';
import { api, ApiError } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { SimpleMarkdown } from '../../components/ui/SimpleMarkdown';
import { useEditorTelemetry } from '../../lib/useEditorTelemetry';
import { ExplanationCheckModal } from '../coding/ExplanationCheckModal';
import { CodeViewer } from '../comprehension/CodeComprehensionPage';

/* Candidates see the work and their own sample runs. Scores and verdicts exist only on the hiring team's side. */

type RoundMeta = { index: number; round_type: string; name: string; time_limit_minutes: number };
type ExamView = {
  id: string; pipeline_id: string; pipeline_title?: string; target_role?: string; candidate_name: string;
  candidate_email: string; access_token: string; status: 'entry_required' | 'in_progress' | 'completed';
  current_round_index: number; rounds: RoundMeta[]; is_invite_token?: boolean; requires_login?: boolean;
  is_practice?: boolean;
};
type Problem = {
  id: string; title: string; difficulty: string; description: string; input_format: string; output_format: string;
  constraints: string[]; starter_code: Record<string, string>; sample_test_cases: { stdin: string; expected_stdout: string }[];
};
type RoundData = {
  index: number; round_type: string; name: string; deadline: string; server_now: string;
  problems?: Problem[]; drafts?: Record<string, { language: string; code: string }>;
  item?: { id: string; title: string; context: string; files: Record<string, string>; questions: { id: string; type: string; prompt: string }[] };
  answers?: Record<string, { answer: string; follow_up: string | null; follow_up_answer?: string; done: boolean }>;
  project?: { title: string; description_markdown: string; instructions: string; repository_files: Record<string, string>; editable_files: string[]; active_file: string };
  files?: Record<string, string>;
  transcript?: { question: string; answer: string | null }[]; current_question?: string | null;
  questions_total?: number; interview_done?: boolean;
};

const ICONS: Record<string, React.ReactNode> = {
  oa_dsa: <Code2 className="w-4 h-4" />, code_comprehension: <Brain className="w-4 h-4" />,
  ai_project: <Boxes className="w-4 h-4" />, tough_interview: <Mic className="w-4 h-4" />,
};
const LANGS: { id: string; label: string; monaco: string }[] = [
  { id: 'python', label: 'Python 3', monaco: 'python' }, { id: 'java', label: 'Java 21', monaco: 'java' },
  { id: 'cpp', label: 'C++20', monaco: 'cpp' },
];

const errText = (e: unknown) => (e instanceof ApiError ? e.message : 'Something went wrong. Try again.');

/* ------------------------------------------------------------------ timer */

const useCountdown = (deadline?: string, serverNow?: string) => {
  const offset = useMemo(() => (serverNow ? new Date(serverNow).getTime() - Date.now() : 0), [serverNow]);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!deadline) return null;
  return Math.max(0, Math.floor((new Date(deadline).getTime() - (now + offset)) / 1000));
};

const Timer: React.FC<{ seconds: number | null }> = ({ seconds }) => {
  if (seconds == null) return null;
  const m = Math.floor(seconds / 60), s = seconds % 60;
  const low = seconds < 120;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-mono text-xs tabular-nums ${low ? 'bg-rose-50 border-rose-200 text-rose-700 animate-pulse' : 'bg-white border-zinc-200 text-zinc-800'}`}>
      <Clock className="w-3.5 h-3.5" /> {seconds === 0 ? "Time's up" : `${m}:${String(s).padStart(2, '0')}`}
    </span>
  );
};

/* ------------------------------------------------------------------ rounds */

const DsaRound: React.FC<{
  round: RoundData; token: string; onCode: (pid: string, lang: string, code: string) => void;
  telemetry: ReturnType<typeof useEditorTelemetry>;
}> = ({ round, token, onCode, telemetry }) => {
  const problems = round.problems || [];
  const [active, setActive] = useState(problems[0]?.id);
  const [sol, setSol] = useState<Record<string, { language: string; code: string }>>(() => {
    const init: Record<string, { language: string; code: string }> = {};
    problems.forEach((p) => {
      init[p.id] = round.drafts?.[p.id] || { language: 'python', code: p.starter_code?.python || '' };
    });
    return init;
  });
  const [run, setRun] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const p = problems.find((x) => x.id === active);
  const cur = p ? sol[p.id] : undefined;

  useEffect(() => {
    Object.entries(sol).forEach(([pid, v]) => onCode(pid, v.language, v.code));
  }, [sol, onCode]);

  if (!p || !cur) return <p className="text-sm text-zinc-500">No problem assigned.</p>;
  const setCode = (code: string) => {
    telemetry.logContentChange(code, cur.code, 0, 'typing');
    setSol((s) => ({ ...s, [p.id]: { ...s[p.id], code } }));
  };
  const setLang = (language: string) =>
    setSol((s) => ({ ...s, [p.id]: { language, code: s[p.id].code.trim() && s[p.id].code !== p.starter_code?.[s[p.id].language] ? s[p.id].code : p.starter_code?.[language] || '' } }));
  const runSamples = async () => {
    setBusy(true); setError(''); setRun(null);
    try {
      await telemetry.flushQueue();
      setRun(await api.post(`/enterprise/assessments/${token}/run`, { problem_id: p.id, language: cur.language, code: cur.code }));
    } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="grid lg:grid-cols-2 gap-4 min-h-[560px]">
      <div className="space-y-3 overflow-auto max-h-[75vh] pr-1">
        {problems.length > 1 && (
          <div className="flex gap-1.5">
            {problems.map((x, i) => (
              <button key={x.id} onClick={() => { setActive(x.id); setRun(null); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border ${x.id === active ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300'}`}>
                Problem {i + 1}
              </button>
            ))}
          </div>
        )}
        <div>
          <h3 className="text-lg font-bold text-zinc-950">{p.title}</h3>
          <span className="text-[11px] font-mono uppercase text-zinc-500">{p.difficulty}</span>
        </div>
        <SimpleMarkdown text={p.description} className="text-sm text-zinc-700" />
        <div className="grid sm:grid-cols-2 gap-3 text-xs">
          <div><p className="font-semibold text-zinc-900 mb-1">Input</p><SimpleMarkdown text={p.input_format} className="text-zinc-600" /></div>
          <div><p className="font-semibold text-zinc-900 mb-1">Output</p><SimpleMarkdown text={p.output_format} className="text-zinc-600" /></div>
        </div>
        {p.constraints?.length > 0 && (
          <ul className="text-xs text-zinc-600 list-disc pl-4 font-mono">{p.constraints.map((c, i) => <li key={i}>{c}</li>)}</ul>
        )}
        {p.sample_test_cases.map((t, i) => (
          <div key={i} className="grid grid-cols-2 gap-2 text-xs font-mono">
            <pre className="p-2 rounded-lg bg-zinc-50 border border-zinc-200 whitespace-pre-wrap">{t.stdin}</pre>
            <pre className="p-2 rounded-lg bg-zinc-50 border border-zinc-200 whitespace-pre-wrap">{t.expected_stdout}</pre>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2 min-h-0">
        <div className="flex items-center justify-between gap-2">
          <select value={cur.language} onChange={(e) => setLang(e.target.value)} aria-label="Language"
            className="text-xs p-2 rounded-lg border border-zinc-200 bg-white font-medium">
            {LANGS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
          </select>
          <Button size="sm" variant="outline" onClick={runSamples} disabled={busy} className="gap-1.5 text-xs">
            <Play className="w-3.5 h-3.5" /> {busy ? 'Running...' : 'Run sample tests'}
          </Button>
        </div>
        <div className="flex-1 min-h-[360px] rounded-xl overflow-hidden border border-zinc-200"
          onKeyDown={(e) => telemetry.logKeyDown(e as any)}
          onPaste={(e) => telemetry.logPaste(e.clipboardData.getData('text'), 0)}>
          <Editor height="100%" language={LANGS.find((l) => l.id === cur.language)?.monaco} theme="vs" value={cur.code}
            onChange={(v) => setCode(v || '')}
            options={{ minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false, automaticLayout: true, tabSize: 4 }} />
        </div>
        {error && <p className="text-xs text-rose-600">{error}</p>}
        {run && (
          <div className="rounded-xl border border-zinc-200 bg-white p-3 space-y-2 text-xs max-h-56 overflow-auto animate-fade-in">
            {run.compile_output && <pre className="text-rose-700 whitespace-pre-wrap font-mono">{run.compile_output}</pre>}
            {(run.results || []).map((t: any) => (
              <div key={t.index} className="space-y-1">
                <p className={`font-semibold flex items-center gap-1 ${t.passed ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {t.passed ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />} Sample {t.index}
                </p>
                {!t.passed && (
                  <pre className="font-mono text-zinc-600 whitespace-pre-wrap">expected: {t.expected}{'\n'}got:      {t.actual || '(nothing)'}{t.stderr ? `\n${t.stderr}` : ''}</pre>
                )}
              </div>
            ))}
            <p className="text-[11px] text-zinc-400">Only sample tests run here. Your submission is checked against the full hidden suite.</p>
          </div>
        )}
      </div>
    </div>
  );
};

const ComprehensionRound: React.FC<{ round: RoundData; token: string; onUpdate: () => void }> = ({ round, token, onUpdate }) => {
  const item = round.item!;
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState(round.answers || {});
  const boxes = useRef<Record<string, HTMLTextAreaElement | null>>({});
  const [focusQ, setFocusQ] = useState(item.questions[0]?.id);

  const submit = async (qid: string) => {
    const text = (drafts[qid] || '').trim();
    if (!text) return;
    setBusy(qid); setError('');
    try {
      const r: any = await api.post(`/enterprise/assessments/${token}/comprehension/answer`, { question_id: qid, answer: text });
      setAnswers((a) => ({
        ...a,
        [qid]: a[qid]?.follow_up ? { ...a[qid], follow_up_answer: text, done: true } : { answer: text, follow_up: r.follow_up, done: r.done },
      }));
      setDrafts((d) => ({ ...d, [qid]: '' }));
      onUpdate();
    } catch (e) { setError(errText(e)); } finally { setBusy(null); }
  };

  return (
    <div className="grid lg:grid-cols-[1.1fr_1fr] gap-4">
      <div className="space-y-2">
        <p className="text-xs text-zinc-600">{item.context}</p>
        <CodeViewer files={item.files} bugLines={[]} onLineClick={(file, line) => {
          const q = focusQ;
          if (!q) return;
          setDrafts((d) => ({ ...d, [q]: `${d[q] ? d[q] + ' ' : ''}${file}:L${line} ` }));
          boxes.current[q]?.focus();
        }} />
      </div>
      <div className="space-y-3 max-h-[75vh] overflow-auto pr-1">
        <p className="text-[11px] text-zinc-500">Don't run anything. Read, reason, answer. A reviewer may ask one follow-up.</p>
        {item.questions.map((q, i) => {
          const a = answers[q.id];
          const done = a?.done;
          return (
            <div key={q.id} className={`rounded-xl border p-3 space-y-2 transition-colors ${done ? 'bg-zinc-50 border-zinc-200' : 'bg-white border-zinc-300'}`}>
              <p className="text-xs font-semibold text-zinc-900"><span className="font-mono text-zinc-400 mr-1">Q{i + 1}</span>{q.prompt}</p>
              {a?.answer && <p className="text-xs text-zinc-600 whitespace-pre-wrap border-l-2 border-zinc-200 pl-2">{a.answer}</p>}
              {a?.follow_up && (
                <p className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-2">Reviewer: {a.follow_up}</p>
              )}
              {a?.follow_up_answer && <p className="text-xs text-zinc-600 whitespace-pre-wrap border-l-2 border-zinc-200 pl-2">{a.follow_up_answer}</p>}
              {done ? (
                <p className="text-[11px] text-zinc-500 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5 text-zinc-400" /> Recorded</p>
              ) : (
                <div className="space-y-1.5">
                  <textarea ref={(el) => { boxes.current[q.id] = el; }} rows={3} value={drafts[q.id] || ''}
                    onFocus={() => setFocusQ(q.id)} onChange={(e) => setDrafts((d) => ({ ...d, [q.id]: e.target.value }))}
                    placeholder={q.type === 'bug' ? 'Name the line (click a line number) and explain the failure.' : 'Your answer'}
                    className="w-full text-xs p-2.5 rounded-lg border border-zinc-200 focus:outline-none focus:ring-1 focus:ring-lime-500" />
                  <div className="flex justify-end">
                    <Button size="sm" onClick={() => submit(q.id)} disabled={busy === q.id || !(drafts[q.id] || '').trim()} className="text-xs gap-1">
                      <Send className="w-3 h-3" /> {busy === q.id ? 'Saving...' : a?.follow_up ? 'Answer follow-up' : 'Submit answer'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
        {error && <p className="text-xs text-rose-600">{error}</p>}
      </div>
    </div>
  );
};

const ProjectRound: React.FC<{
  round: RoundData; token: string; onFiles: (f: Record<string, string>) => void; telemetry: ReturnType<typeof useEditorTelemetry>;
}> = ({ round, token, onFiles, telemetry }) => {
  const proj = round.project!;
  const [files, setFiles] = useState<Record<string, string>>(() => {
    const f: Record<string, string> = {};
    proj.editable_files.forEach((n) => { f[n] = round.files?.[n] ?? proj.repository_files[n] ?? ''; });
    return f;
  });
  const names = Object.keys(proj.repository_files);
  const [active, setActive] = useState(proj.active_file || proj.editable_files[0]);
  const [run, setRun] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { onFiles(files); }, [files, onFiles]);
  const editable = proj.editable_files.includes(active);

  const runTests = async () => {
    setBusy(true); setError(''); setRun(null);
    try { setRun(await api.post(`/enterprise/assessments/${token}/run-project`, { files })); }
    catch (e) { setError(errText(e)); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-3">
      <details className="rounded-xl border border-zinc-200 bg-zinc-50 p-3" open>
        <summary className="text-sm font-bold text-zinc-900 cursor-pointer">{proj.title}</summary>
        <SimpleMarkdown text={proj.description_markdown} className="text-xs text-zinc-700 mt-2" />
      </details>
      <div className="flex flex-wrap items-center gap-1">
        {names.map((n) => (
          <button key={n} onClick={() => setActive(n)}
            className={`px-2.5 py-1 rounded-md text-[11px] font-mono border ${n === active ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-600 border-zinc-200'}`}>
            {n}{proj.editable_files.includes(n) ? '' : ' (read-only)'}
          </button>
        ))}
        <Button size="sm" variant="outline" onClick={runTests} disabled={busy} className="ml-auto gap-1.5 text-xs">
          <Play className="w-3.5 h-3.5" /> {busy ? 'Running tests...' : 'Run tests'}
        </Button>
      </div>
      <div className="h-[420px] rounded-xl overflow-hidden border border-zinc-200" onKeyDown={(e) => telemetry.logKeyDown(e as any)}
        onPaste={(e) => telemetry.logPaste(e.clipboardData.getData('text'), 0)}>
        <Editor height="100%" language="python" theme="vs" path={active}
          value={editable ? files[active] : proj.repository_files[active]}
          onChange={(v) => { if (editable) { telemetry.logContentChange(v || '', files[active], 0, 'typing'); setFiles((f) => ({ ...f, [active]: v || '' })); } }}
          options={{ readOnly: !editable, minimap: { enabled: false }, fontSize: 13, automaticLayout: true, scrollBeyondLastLine: false }} />
      </div>
      {error && <p className="text-xs text-rose-600">{error}</p>}
      {run && (
        <div className="rounded-xl border border-zinc-200 bg-white p-3 text-xs space-y-1 max-h-60 overflow-auto animate-fade-in">
          <p className="font-semibold">{run.passed_tests} passed · {run.failed_tests} failed</p>
          {(run.test_results || []).filter((t: any) => t.status !== 'passed').map((t: any) => (
            <div key={t.name}><p className="font-mono text-rose-700">{t.name}</p><pre className="text-zinc-600 whitespace-pre-wrap">{t.error_message}</pre></div>
          ))}
          {!run.test_results?.length && <pre className="whitespace-pre-wrap text-zinc-600">{run.raw_output}</pre>}
        </div>
      )}
    </div>
  );
};

const InterviewRound: React.FC<{ round: RoundData; token: string; onRound: (r: RoundData) => void }> = ({ round, token, onRound }) => {
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [round.transcript?.length]);
  const send = async () => {
    if (!answer.trim()) return;
    setBusy(true); setError('');
    try { onRound(await api.post(`/enterprise/assessments/${token}/interview/answer`, { answer })); setAnswer(''); }
    catch (e) { setError(errText(e)); } finally { setBusy(false); }
  };
  const tr = round.transcript || [];
  return (
    <div className="max-w-3xl mx-auto space-y-3">
      <p className="text-[11px] text-zinc-500 text-center">
        {round.questions_total} questions. The interviewer may ask about the code you wrote earlier. Answer like you would out loud.
      </p>
      <div className="space-y-3">
        {tr.map((t, i) => (
          <div key={i} className="space-y-2 animate-fade-in">
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-zinc-900 text-lime-400 flex items-center justify-center shrink-0 text-[11px] font-bold">AI</div>
              <p className="text-sm text-zinc-900 bg-white border border-zinc-200 rounded-2xl rounded-tl-sm px-3 py-2">{t.question}</p>
            </div>
            {t.answer && <p className="ml-9 text-sm text-zinc-700 bg-lime-50/60 border border-lime-200/70 rounded-2xl rounded-tr-sm px-3 py-2 whitespace-pre-wrap">{t.answer}</p>}
          </div>
        ))}
        <div ref={end} />
      </div>
      {round.current_question ? (
        <div className="space-y-2">
          <textarea rows={4} value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Your answer"
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send(); }}
            className="w-full text-sm p-3 rounded-xl border border-zinc-200 focus:outline-none focus:ring-1 focus:ring-lime-500" />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-zinc-400 font-mono">Question {tr.length} of {round.questions_total} · Ctrl+Enter to send</span>
            <Button size="sm" onClick={send} disabled={busy || !answer.trim()} className="gap-1 text-xs"><Send className="w-3 h-3" /> {busy ? 'Sending...' : 'Send'}</Button>
          </div>
        </div>
      ) : (
        round.interview_done && <p className="text-center text-sm text-zinc-600">That's all the questions. Submit the round to finish.</p>
      )}
      {error && <p className="text-xs text-rose-600">{error}</p>}
    </div>
  );
};

/* Practice simulations only: the candidate's own full report, with answer keys. */
const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v)}%`);

const PracticeReport: React.FC<{ token: string; title?: string }> = ({ token, title }) => {
  const [rep, setRep] = useState<any>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.get(`/enterprise/assessments/${token}/report`).then(setRep).catch((e) => setError(errText(e)));
  }, [token]);
  if (error) return <Card className="p-6 text-sm text-rose-700">{error}</Card>;
  if (!rep) return <div className="h-64 rounded-2xl bg-zinc-100 animate-pulse" />;
  return (
    <div className="space-y-4 max-w-4xl mx-auto animate-fade-in">
      <Card className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-xs font-mono text-zinc-500 uppercase">Simulation report</p>
          <h2 className="text-xl font-bold text-zinc-950">{title}</h2>
          <p className="text-xs text-zinc-500">Graded the same way a hiring team would see it. Unscored rounds don't count toward the total.</p>
        </div>
        <div className="text-right">
          <p className="text-4xl font-extrabold font-mono text-zinc-950 tabular-nums">{pct(rep.composite_score)}</p>
          <p className="text-[11px] text-zinc-500">overall</p>
        </div>
      </Card>
      {rep.rounds.map((r: any) => {
        const d = r.details || {};
        return (
          <Card key={r.index} className="p-5 space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-bold text-sm text-zinc-900 flex items-center gap-2">{ICONS[r.round_type]} {r.name}</h3>
              <span className="font-mono font-bold text-lg text-zinc-950">{r.status === 'not_evaluated' ? 'not evaluated' : pct(r.score)}</span>
            </div>
            <div className="h-1.5 rounded-full bg-zinc-100 overflow-hidden">
              <div className="h-full bg-lime-500 transition-all duration-700" style={{ width: `${Math.max(0, Math.min(100, r.score || 0))}%` }} />
            </div>
            {d.problems && Object.entries(d.problems).map(([pid, p]: [string, any]) => (
              <p key={pid} className="text-xs text-zinc-600 font-mono">
                {pid}: {p.status === 'not_attempted' ? 'not attempted' : `${p.tests_passed}/${p.tests_total} hidden tests passed (${p.language})`}
              </p>
            ))}
            {typeof d.passed_tests === 'number' && <p className="text-xs text-zinc-600 font-mono">{d.passed_tests}/{d.total_tests} repository tests passed</p>}
            {d.status === 'not_attempted' && <p className="text-xs text-zinc-500">Not attempted.</p>}
            {d.per_question && d.answer_key && (
              <div className="space-y-2">
                {Object.entries(d.per_question).map(([q, v]: [string, any]) => (
                  <div key={q} className="text-xs">
                    <p className="font-semibold text-zinc-800">{q.toUpperCase()} · {Math.round(v * 100)}%</p>
                    {d.answer_key.questions?.[q]?.expected_output && <p className="font-mono text-zinc-600">Expected output: {d.answer_key.questions[q].expected_output}</p>}
                    {(d.answer_key.questions?.[q]?.key_points || []).length > 0 && (
                      <ul className="list-disc pl-4 text-zinc-600">{d.answer_key.questions[q].key_points.map((k: string, i: number) => <li key={i}>{k}</li>)}</ul>
                    )}
                  </div>
                ))}
                {d.answer_key.bug_lines?.length > 0 && (
                  <p className="text-xs text-rose-700 font-mono">Bug: {d.answer_key.bug_lines.map((b: any) => `${b.file}:L${b.line}`).join(', ')}</p>
                )}
              </div>
            )}
            {d.summary && <p className="text-sm text-zinc-700">{d.summary}</p>}
            {(d.strengths?.length > 0 || d.concerns?.length > 0) && (
              <div className="grid sm:grid-cols-2 gap-3 text-xs">
                {d.strengths?.length > 0 && <ul className="space-y-1"><li className="font-semibold text-emerald-700">Held up</li>{d.strengths.map((x: string, i: number) => <li key={i} className="text-zinc-600">{x}</li>)}</ul>}
                {d.concerns?.length > 0 && <ul className="space-y-1"><li className="font-semibold text-rose-700">Didn't</li>{d.concerns.map((x: string, i: number) => <li key={i} className="text-zinc-600">{x}</li>)}</ul>}
              </div>
            )}
            {r.status === 'not_evaluated' && <p className="text-xs text-zinc-500">Connect an AI model in Settings to get interview grading.</p>}
            {r.overtime && <p className="text-xs text-amber-700">Submitted after the time limit.</p>}
          </Card>
        );
      })}
      <div className="flex justify-center gap-2">
        <Link to="/tracks"><Button variant="outline">Back to simulations</Button></Link>
      </div>
    </div>
  );
};

/* A render error in one round must not blank the exam: the candidate keeps the header, timer and submit. */
class RoundBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? (
      <div className="p-6 rounded-xl border border-rose-200 bg-rose-50 text-sm text-rose-800">
        This round's screen failed to load. Reload the page; your saved work and the timer are kept on the server.
      </div>
    ) : this.props.children;
  }
}

/* ------------------------------------------------------------------ page */

export const CandidateAssessmentPage: React.FC = () => {
  const { token: urlToken } = useParams<{ token: string }>();
  const { user } = useAuth();
  const [view, setView] = useState<ExamView | null>(null);
  const [round, setRound] = useState<RoundData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fatal, setFatal] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [resume, setResume] = useState('');
  const [blurs, setBlurs] = useState(0);
  const [blurToast, setBlurToast] = useState(false);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [explain, setExplain] = useState<{ key: string; title: string } | null>(null);
  const codeRef = useRef<Record<string, { language: string; code: string }>>({});
  const filesRef = useRef<Record<string, string>>({});

  const token = view?.access_token || urlToken || '';
  const isCodingRound = round?.round_type === 'oa_dsa' || round?.round_type === 'ai_project';
  const telemetry = useEditorTelemetry({
    roundKey: String(view?.current_round_index ?? 0), candidateToken: view?.access_token,
    enabled: Boolean(view?.access_token && isCodingRound),
  });
  const remaining = useCountdown(round?.deadline, round?.server_now);

  const loadRound = useCallback(async (tok: string) => {
    setRound(null);
    try { setRound(await api.get<RoundData>(`/enterprise/assessments/${tok}/round`)); }
    catch (e) { setError(errText(e)); }
  }, []);

  useEffect(() => {
    if (!urlToken) return;
    setLoading(true);
    api.get<ExamView>(`/enterprise/assessments/${urlToken}`)
      .then(setView)
      .catch(() => setFatal('This assessment link is invalid or has expired.'))
      .finally(() => setLoading(false));
  }, [urlToken, user?.id]);

  // The next round's clock starts on fetch, so wait until the post-code explanation check is finished.
  useEffect(() => {
    if (view?.access_token && view.status === 'in_progress' && !explain) loadRound(view.access_token);
  }, [view?.access_token, view?.status, view?.current_round_index, explain, loadRound]);

  useEffect(() => {
    if (!view?.access_token || view.status !== 'in_progress') return;
    const onBlur = () => { setBlurs((b) => b + 1); setBlurToast(true); setTimeout(() => setBlurToast(false), 4000); };
    window.addEventListener('blur', onBlur);
    return () => window.removeEventListener('blur', onBlur);
  }, [view?.access_token, view?.status]);

  const enter = async () => {
    setBusy(true); setError('');
    try {
      setView(await api.post<ExamView>(`/enterprise/assessments/entry/${urlToken}`, name.trim().length >= 2 ? { candidate_name: name.trim() } : {}));
    } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  };

  const onCode = useCallback((pid: string, language: string, code: string) => { codeRef.current[pid] = { language, code }; }, []);
  const onFiles = useCallback((f: Record<string, string>) => { filesRef.current = f; }, []);

  const submitRound = async () => {
    if (!view || !round) return;
    setBusy(true); setError(''); setConfirmSubmit(false);
    try {
      if (isCodingRound) await telemetry.flushQueue();
      const payload: Record<string, any> = {
        round_index: round.index, round_type: round.round_type,
        submission_data: round.round_type === 'oa_dsa' ? { solutions: codeRef.current } : round.round_type === 'ai_project' ? { files: filesRef.current } : {},
        integrity_events: { window_blurs: blurs },
      };
      if (round.index === 0 && resume.trim()) payload.resume_text = resume.trim();
      const next = await api.post<ExamView>(`/enterprise/assessments/${view.access_token}/submit-round`, payload);
      setBlurs(0);
      codeRef.current = {};
      filesRef.current = {};
      if (round.round_type === 'oa_dsa') setExplain({ key: String(round.index), title: round.problems?.[0]?.title || round.name });
      setView(next);
    } catch (e) { setError(errText(e)); } finally { setBusy(false); }
  };

  const nextPath = `/assess/take/${urlToken}`;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  if (fatal || !view) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 p-4">
        <Card className="max-w-md p-8 text-center space-y-3">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-lg font-bold text-zinc-900">Assessment unavailable</h2>
          <p className="text-xs text-zinc-500">{fatal}</p>
        </Card>
      </div>
    );
  }

  const header = (
    <header className="bg-white/90 backdrop-blur border-b border-zinc-200 px-4 sm:px-6 py-3 flex items-center justify-between gap-3 sticky top-0 z-30">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-zinc-900 flex items-center justify-center shrink-0"><Building2 className="w-5 h-5 text-lime-400" /></div>
        <div className="min-w-0">
          <h1 className="font-bold text-sm text-zinc-950 truncate">{view.pipeline_title}</h1>
          <p className="text-[11px] text-zinc-500 truncate">{view.target_role}{view.candidate_name ? ` · ${view.candidate_name}` : ''}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {round && view.status === 'in_progress' && <Timer seconds={remaining} />}
        {view.status === 'in_progress' && (
          <span className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-mono ${blurs > 2 ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-zinc-50 border-zinc-200 text-zinc-600'}`}>
            {blurs > 2 ? <ShieldAlert className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />} Focus tracked
          </span>
        )}
      </div>
    </header>
  );

  const stepper = (
    <ol className="flex gap-2 overflow-x-auto pb-1">
      {view.rounds.map((r) => {
        const done = view.status === 'completed' || r.index < view.current_round_index;
        const cur = view.status === 'in_progress' && r.index === view.current_round_index;
        return (
          <li key={r.index} className={`flex-1 min-w-[150px] p-3 rounded-xl border text-xs transition-all ${cur ? 'bg-white border-lime-500 shadow-sm' : done ? 'bg-lime-50/50 border-lime-200' : 'bg-zinc-100/60 border-zinc-200 text-zinc-400'}`}>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase tracking-wider">{ICONS[r.round_type]} Round {r.index + 1}</span>
              {done ? <CheckCircle2 className="w-3.5 h-3.5 text-lime-600" /> : <span className="text-[10px] font-mono">{r.time_limit_minutes}m</span>}
            </div>
            <p className={`mt-1 font-semibold truncate ${cur || done ? 'text-zinc-900' : ''}`}>{r.name}</p>
          </li>
        );
      })}
    </ol>
  );

  // Landing: invite link
  if (view.status === 'entry_required') {
    return (
      <div className="min-h-screen bg-zinc-50/60 flex flex-col">
        {header}
        <main className="flex-1 max-w-2xl mx-auto w-full p-4 sm:p-8 space-y-6 animate-fade-in">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold text-zinc-950">You're invited to {view.pipeline_title}</h2>
            <p className="text-sm text-zinc-600">{view.rounds.length} timed rounds for {view.target_role}. Each round's clock starts when you open it.</p>
          </div>
          {stepper}
          <Card className="p-6 space-y-4">
            <ul className="text-xs text-zinc-600 space-y-1.5">
              <li className="flex gap-2"><Lock className="w-3.5 h-3.5 mt-0.5 text-zinc-400" /> Your results go to the hiring team. You won't see scores here.</li>
              <li className="flex gap-2"><ShieldCheck className="w-3.5 h-3.5 mt-0.5 text-zinc-400" /> Tab switches and editor activity are recorded for the hiring team.</li>
              <li className="flex gap-2"><Clock className="w-3.5 h-3.5 mt-0.5 text-zinc-400" /> Rounds go in order. Once you submit a round you can't go back.</li>
            </ul>
            {view.requires_login || !user ? (
              <div className="flex flex-col sm:flex-row gap-2">
                <Link to={`/login?next=${encodeURIComponent(nextPath)}`} className="flex-1">
                  <Button className="w-full gap-2">Sign in to start <ArrowRight className="w-4 h-4 text-lime-400" /></Button>
                </Link>
                <Link to={`/register?next=${encodeURIComponent(nextPath)}`} className="flex-1">
                  <Button variant="outline" className="w-full">Create an account</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <Input label="Name the hiring team will see" placeholder={user.email} value={name} onChange={(e) => setName(e.target.value)} />
                <p className="text-[11px] text-zinc-500">Signed in as <span className="font-mono">{user.email}</span>.</p>
                {error && <p className="text-xs text-rose-600">{error}</p>}
                <Button onClick={enter} disabled={busy} className="w-full gap-2">{busy ? 'Starting...' : 'Start or resume'} <ArrowRight className="w-4 h-4 text-lime-400" /></Button>
              </div>
            )}
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50/60 flex flex-col">
      {header}
      {blurToast && (
        <div role="status" className="fixed top-16 right-4 z-50 bg-amber-500 text-white px-4 py-2.5 rounded-xl shadow-lg text-xs font-medium animate-fade-in">
          {view.is_practice ? 'Focus left the window. In a real assessment this is reported to the hiring team.' : 'Focus left the assessment window. This is logged for the hiring team.'}
        </div>
      )}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 sm:p-6 space-y-4">
        {stepper}
        {view.status === 'completed' && view.is_practice ? (
          <PracticeReport token={view.access_token} title={view.pipeline_title} />
        ) : view.status === 'completed' ? (
          <Card className="p-10 text-center space-y-4 max-w-xl mx-auto animate-fade-in">
            <div className="w-16 h-16 rounded-full bg-lime-50 border border-lime-200 flex items-center justify-center mx-auto"><CheckCircle2 className="w-8 h-8 text-lime-700" /></div>
            <h2 className="text-2xl font-bold text-zinc-950">Submitted</h2>
            <p className="text-sm text-zinc-600">All rounds are in. {view.pipeline_title}'s hiring team will review your work and contact you. Results aren't shown here.</p>
            <Link to="/"><Button variant="outline">Back to Skill Issue</Button></Link>
          </Card>
        ) : explain ? (
          <Card className="p-8 text-center text-sm text-zinc-600">Answer the follow-up questions about your code. The next round starts after that.</Card>
        ) : !round ? (
          error ? <Card className="p-6 text-sm text-rose-700">{error}</Card> :
            <div className="h-96 rounded-2xl bg-zinc-100 animate-pulse" />
        ) : (
          <Card className="p-4 sm:p-6 space-y-4 animate-fade-in" key={round.index}>
            <div className="flex items-center justify-between gap-3 pb-3 border-b border-zinc-100">
              <h2 className="font-bold text-base text-zinc-950 flex items-center gap-2">{ICONS[round.round_type]} {round.name}</h2>
              <span className="text-[11px] font-mono text-zinc-500">Round {round.index + 1} of {view.rounds.length}</span>
            </div>
            {round.index === 0 && round.round_type !== 'tough_interview' && (
              <details className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                <summary className="text-xs font-semibold text-zinc-800 cursor-pointer flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> Optional: paste your resume so the interviewer can ask about your background</summary>
                <textarea rows={3} value={resume} onChange={(e) => setResume(e.target.value)}
                  className="mt-2 w-full text-xs p-2.5 rounded-lg border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-lime-500" />
              </details>
            )}
            <RoundBoundary>
            {round.round_type === 'oa_dsa' && <DsaRound round={round} token={token} onCode={onCode} telemetry={telemetry} />}
            {round.round_type === 'code_comprehension' && <ComprehensionRound round={round} token={token} onUpdate={() => undefined} />}
            {round.round_type === 'ai_project' && <ProjectRound round={round} token={token} onFiles={onFiles} telemetry={telemetry} />}
            {round.round_type === 'tough_interview' && <InterviewRound round={round} token={token} onRound={setRound} />}
            </RoundBoundary>
            {error && <p className="text-xs text-rose-600">{error}</p>}
            <div className="pt-3 border-t border-zinc-100 flex items-center justify-end gap-2">
              {confirmSubmit ? (
                <>
                  <span className="text-xs text-zinc-600">Submit this round? You can't come back to it.</span>
                  <Button size="sm" variant="outline" onClick={() => setConfirmSubmit(false)}>Keep working</Button>
                  <Button size="sm" onClick={submitRound} disabled={busy}>{busy ? 'Submitting...' : 'Yes, submit'}</Button>
                </>
              ) : (
                <Button onClick={() => setConfirmSubmit(true)} disabled={busy} className="gap-2 text-xs">
                  {round.index === view.rounds.length - 1 ? 'Finish assessment' : 'Submit round'} <ArrowRight className="w-3.5 h-3.5 text-lime-400" />
                </Button>
              )}
            </div>
          </Card>
        )}
      </main>
      {explain && (
        <ExplanationCheckModal isOpen mode="assessment" submissionRef={`oa_round_${explain.key}`} roundKey={explain.key}
          problemTitle={explain.title} candidateAssessmentId={view.id} candidateToken={view.access_token}
          onComplete={() => setExplain(null)} onClose={() => setExplain(null)} />
      )}
    </div>
  );
};
