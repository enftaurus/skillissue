import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Boxes, Brain, Building2, FileText, Mic, Search } from 'lucide-react';
import { api } from '../../lib/api';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { PageSkeleton } from '../../components/ui/Skeleton';
import { PromptAnalysisModal } from '../projects/PromptAnalysisModal';

type Report = {
  kind: 'interview' | 'ai_prompt' | 'comprehension' | 'simulation';
  id: string; title: string; subtitle: string; score: number | null; status: string; created_at: string | null; link: string;
};

const KINDS: { id: 'all' | Report['kind']; label: string; icon: React.ReactNode }[] = [
  { id: 'all', label: 'All', icon: <FileText className="w-3.5 h-3.5" /> },
  { id: 'interview', label: 'Interviews', icon: <Mic className="w-3.5 h-3.5" /> },
  { id: 'ai_prompt', label: 'AI prompt analysis', icon: <Boxes className="w-3.5 h-3.5" /> },
  { id: 'comprehension', label: 'Code comprehension', icon: <Brain className="w-3.5 h-3.5" /> },
  { id: 'simulation', label: 'Simulations', icon: <Building2 className="w-3.5 h-3.5" /> },
];
const ICON: Record<Report['kind'], React.ReactNode> = {
  interview: <Mic className="w-4 h-4" />, ai_prompt: <Boxes className="w-4 h-4" />,
  comprehension: <Brain className="w-4 h-4" />, simulation: <Building2 className="w-4 h-4" />,
};

const scoreTone = (s: number | null) =>
  s == null ? 'text-zinc-400' : s >= 70 ? 'text-emerald-700' : s >= 40 ? 'text-amber-700' : 'text-rose-700';

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<Report[] | null>(null);
  const [kind, setKind] = useState<'all' | Report['kind']>('all');
  const [q, setQ] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Report[]>('/reports').then(setReports).catch((e) => setError(e?.message || 'Could not load reports.'));
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: reports?.length || 0 };
    (reports || []).forEach((r) => { c[r.kind] = (c[r.kind] || 0) + 1; });
    return c;
  }, [reports]);
  const shown = (reports || []).filter((r) => (kind === 'all' || r.kind === kind)
    && (!q.trim() || `${r.title} ${r.subtitle}`.toLowerCase().includes(q.trim().toLowerCase())));

  if (!reports && !error) return <PageSkeleton />;
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-zinc-950">Reports</h1>
        <p className="text-sm text-zinc-600">Every past evaluation in one place: interviews, AI prompt analysis, code comprehension and simulations.</p>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div className="flex flex-wrap gap-1.5">
          {KINDS.map((k) => (
            <button key={k.id} onClick={() => setKind(k.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${kind === k.id ? 'bg-zinc-900 text-white border-zinc-900' : 'bg-white text-zinc-600 border-zinc-200 hover:border-zinc-300'}`}>
              {k.icon} {k.label} <span className="font-mono opacity-70">{counts[k.id] || 0}</span>
            </button>
          ))}
        </div>
        <label className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search reports" aria-label="Search reports"
            className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-lime-500 w-full sm:w-56" />
        </label>
      </div>
      {error && <Card className="p-4 text-sm text-rose-700">{error}</Card>}
      {shown.length === 0 && !error ? (
        <Card className="p-10 text-center text-sm text-zinc-500">No reports here yet.</Card>
      ) : (
        <ul className="space-y-2">
          {shown.map((r) => (
            <li key={`${r.kind}-${r.id}`}>
              <Link to={r.link} className="flex items-center gap-4 p-4 rounded-xl bg-white border border-zinc-200 hover:border-zinc-300 hover:shadow-sm transition-all">
                <span className="w-9 h-9 rounded-xl bg-zinc-100 text-zinc-700 flex items-center justify-center shrink-0">{ICON[r.kind]}</span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-zinc-950 truncate">{r.title}</span>
                  <span className="block text-xs text-zinc-500 truncate">{r.subtitle}{r.status === 'ended for conduct' ? ' · ended for conduct' : ''}</span>
                </span>
                <span className="text-right shrink-0">
                  <span className={`block text-lg font-bold font-mono tabular-nums ${scoreTone(r.score)}`}>{r.score == null ? '—' : `${Math.round(r.score)}%`}</span>
                  <span className="block text-[11px] text-zinc-400">{r.created_at ? new Date(r.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

/* A past AI-project submission, reopened with the same analysis view shown right after submitting. */
export const ProjectReportPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.get(`/reports/projects/${id}`).then(setData).catch((e) => setError(e?.message || 'Report not found.'));
  }, [id]);
  if (error) return <div className="max-w-xl mx-auto p-8"><Card className="p-6 text-sm text-rose-700">{error}</Card></div>;
  if (!data) return <PageSkeleton />;
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-3">
      <Button variant="outline" size="sm" onClick={() => navigate('/reports')}>Back to reports</Button>
      <Card className="p-5">
        <p className="text-xs font-mono text-zinc-500 uppercase">AI prompt analysis</p>
        <h1 className="text-xl font-bold text-zinc-950">{data.project_title}</h1>
        <p className="text-xs text-zinc-500">Submitted {new Date(data.created_at).toLocaleString()} · {data.prompts_count} prompts</p>
      </Card>
      <PromptAnalysisModal isOpen onClose={() => navigate('/reports')} data={data.prompt_analysis}
        testsPassed={data.passed_tests} totalTests={data.total_tests} timeSpentSeconds={data.time_spent_seconds} />
    </div>
  );
};
