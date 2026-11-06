import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { AssessmentPipeline, PipelineLeaderboard, RoundConfig, CandidateAssessment } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Modal } from '../../components/ui/Modal';
import {
  Building2,
  Users,
  Plus,
  Copy,
  Check,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Code2,
  Mic,
  Boxes,
  FileText,
  Terminal,
  Activity,
} from 'lucide-react';
import { EditorReplayModal } from './EditorReplayModal';

type CatalogEntry = { id: string; title: string; meta?: string };

const blurCount = (v: any): number =>
  typeof v === 'number' ? v : v && typeof v === 'object' ? Object.values(v).reduce((a: number, b: any) => a + (Number(b) || 0), 0) : 0;

const RoundDetails: React.FC<{ data: any }> = ({ data }) => {
  const d = data?.details || {};
  return (
    <div className="w-full text-[11px] text-zinc-600 space-y-1">
      {d.problems &&
        Object.entries(d.problems).map(([pid, p]: [string, any]) => (
          <p key={pid} className="font-mono">
            {pid}: {p.status === 'not_attempted' ? 'not attempted' : `${p.tests_passed}/${p.tests_total} tests (${p.language})`}
          </p>
        ))}
      {d.per_question && (
        <p className="font-mono">
          {d.item_id}: {Object.entries(d.per_question).map(([q, v]: [string, any]) => `${q} ${Math.round(v * 100)}%`).join(' · ')}
        </p>
      )}
      {typeof d.passed_tests === 'number' && <p className="font-mono">{d.passed_tests}/{d.total_tests} project tests</p>}
      {d.summary && <p className="italic">{d.summary}</p>}
      {Array.isArray(d.transcript) && d.transcript.length > 0 && (
        <details>
          <summary className="cursor-pointer text-zinc-800 font-semibold">Interview transcript ({d.answered}/{d.questions_total} answered)</summary>
          <div className="mt-1 space-y-1.5">
            {d.transcript.map((t: any, i: number) => (
              <div key={i}>
                <p className="font-semibold text-zinc-800">Q{i + 1}. {t.question}</p>
                <p className="whitespace-pre-wrap">{t.answer || '(no answer)'}</p>
              </div>
            ))}
          </div>
        </details>
      )}
      {data?.overtime && <p className="text-amber-700">Submitted after the time limit.</p>}
    </div>
  );
};

export const EnterprisePortalPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pipelines' | 'leaderboard'>('pipelines');
  const [pipelines, setPipelines] = useState<AssessmentPipeline[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<PipelineLeaderboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Candidate Audit & Telemetry Replay Modal State
  const [selectedCandidateForAudit, setSelectedCandidateForAudit] = useState<CandidateAssessment | null>(null);
  const [replayCandidate, setReplayCandidate] = useState<CandidateAssessment | null>(null);

  // Create Pipeline Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pipelineTitle, setPipelineTitle] = useState('');
  const [targetRole, setTargetRole] = useState('Software Development Engineer');
  const [jobDescription, setJobDescription] = useState('');
  const [catalog, setCatalog] = useState<{ problems: CatalogEntry[]; projects: CatalogEntry[]; items: CatalogEntry[] }>({
    problems: [], projects: [], items: [],
  });

  const [rounds, setRounds] = useState<RoundConfig[]>([
    {
      round_type: 'oa_dsa',
      name: 'Coding assessment',
      time_limit_minutes: 35,
      is_enabled: true,
      config: { problems_count: 2, difficulty: 'medium', problem_ids: [] },
    },
    {
      round_type: 'code_comprehension',
      name: 'Code comprehension (read, trace, find the bug)',
      time_limit_minutes: 20,
      is_enabled: true,
      config: { item_id: '' },
    },
    {
      round_type: 'ai_project',
      name: 'Project work in a real repository',
      time_limit_minutes: 30,
      is_enabled: false,
      config: { project_id: 'distributed-rate-limiter' },
    },
    {
      round_type: 'tough_interview',
      name: 'Technical interview',
      time_limit_minutes: 20,
      is_enabled: true,
      config: { questions_count: 4 },
    },
  ]);
  const updateRound = (idx: number, patch: Partial<RoundConfig>, cfg?: Record<string, any>) => {
    setRounds((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch, config: { ...r.config, ...(cfg || {}) } } : r)));
  };
  const moveRound = (idx: number, dir: -1 | 1) => {
    setRounds((prev) => {
      const j = idx + dir;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  };

  const [modelConnected, setModelConnected] = useState<boolean | null>(null);
  useEffect(() => {
    api.get<{ provider_name?: string }>('/providers/config')
      .then((c) => setModelConnected(Boolean(c?.provider_name) && c.provider_name !== 'mock'))
      .catch(() => setModelConnected(false));
  }, []);

  useEffect(() => {
    Promise.all([
      api.get<any[]>('/coding/problems').catch(() => []),
      api.get<any[]>('/projects').catch(() => []),
      api.get<any[]>('/comprehension/items').catch(() => []),
    ]).then(([problems, projects, items]) =>
      setCatalog({
        problems: problems.map((p) => ({ id: p.id, title: p.title, meta: p.difficulty })),
        projects: projects.map((p) => ({ id: p.id, title: p.title, meta: p.difficulty })),
        items: items.map((i) => ({ id: i.id, title: i.title, meta: i.difficulty })),
      })
    );
  }, []);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Invite Candidate Modal State
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [candidateName, setCandidateName] = useState('');
  const [candidateEmail, setCandidateEmail] = useState('');
  const [isInviting, setIsInviting] = useState(false);

  const loadPipelines = async () => {
    try {
      setLoading(true);
      const data = await api.get<AssessmentPipeline[]>('/enterprise/pipelines');
      setPipelines(data);
      if (data.length > 0 && !selectedPipelineId) {
        setSelectedPipelineId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load pipelines', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPipelines();
  }, []);

  useEffect(() => {
    if (selectedPipelineId && activeTab === 'leaderboard') {
      api.get<PipelineLeaderboard>(`/enterprise/pipelines/${selectedPipelineId}/leaderboard`)
        .then(setLeaderboard)
        .catch((err) => console.error('Failed to load leaderboard', err));
    }
  }, [selectedPipelineId, activeTab]);

  const handleCreatePipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pipelineTitle.trim() || !jobDescription.trim()) return;

    try {
      setIsSubmitting(true);
      await api.post('/enterprise/pipelines', {
        title: pipelineTitle,
        target_role: targetRole,
        job_description: jobDescription,
        rounds: rounds.map((r) => ({
          ...r,
          config: Object.fromEntries(Object.entries(r.config || {}).filter(([, v]) => v !== '' && !(Array.isArray(v) && v.length === 0))),
        })),
        oa_config: { mode: 'curated' },
      });
      setIsCreateOpen(false);
      setPipelineTitle('');
      setJobDescription('');
      loadPipelines();
    } catch (err) {
      console.error('Failed to create pipeline', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInviteCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPipelineId || !candidateName.trim() || !candidateEmail.trim()) return;

    try {
      setIsInviting(true);
      await api.post(`/enterprise/pipelines/${selectedPipelineId}/invite`, {
        candidate_name: candidateName,
        candidate_email: candidateEmail,
      });
      setIsInviteOpen(false);
      setCandidateName('');
      setCandidateEmail('');
      loadPipelines();
      if (activeTab === 'leaderboard') {
        const lb = await api.get<PipelineLeaderboard>(`/enterprise/pipelines/${selectedPipelineId}/leaderboard`);
        setLeaderboard(lb);
      }
    } catch (err) {
      console.error('Failed to invite candidate', err);
    } finally {
      setIsInviting(false);
    }
  };

  const copyInviteLink = (inviteUrl: string, id: string) => {
    const fullUrl = `${window.location.origin}${inviteUrl}`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in bg-zinc-50/40 min-h-screen">
      {/* Header */}
      <div className="bg-white border border-zinc-200 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-50 border border-lime-200 text-lime-800 text-xs font-semibold">
            <Building2 className="w-3.5 h-3.5 text-lime-700" />
            Enterprise &amp; Campus Placement Assessment Portal
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-950">
            Recruitment Assessment Hub
          </h1>
          <p className="text-xs sm:text-sm text-zinc-600 leading-relaxed">
            Configure multi-round candidate assessments: OA DSA (Preset, Custom URL, or Codeforces randomizer), AI Systems take-home project, and oral technical interviews that cross-examine candidates on their submitted OA code to catch cheating.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => setIsCreateOpen(true)}
            className="gap-2 bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold rounded-xl"
          >
            <Plus className="w-4 h-4 text-lime-400" />
            <span>New Hiring Assessment</span>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-200 pb-2 text-xs font-medium">
        <button
          onClick={() => setActiveTab('pipelines')}
          className={`px-4 py-2 rounded-xl transition-all ${
            activeTab === 'pipelines'
              ? 'bg-zinc-900 text-white font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
          }`}
        >
          Assessment Pipelines ({pipelines.length})
        </button>
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2 rounded-xl transition-all ${
            activeTab === 'leaderboard'
              ? 'bg-zinc-900 text-white font-bold shadow-xs'
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
          }`}
        >
          Candidate Leaderboard &amp; Anti-Cheating Telemetry
        </button>
      </div>

      {/* TAB 1: Pipelines */}
      {activeTab === 'pipelines' && (
        <div className="space-y-6">
          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-zinc-500 font-mono">Loading pipelines...</p>
            </div>
          ) : pipelines.length === 0 ? (
            <Card className="p-12 text-center space-y-4 rounded-2xl border-zinc-200 bg-white">
              <Building2 className="w-12 h-12 text-zinc-400 mx-auto" />
              <h3 className="font-bold text-base text-zinc-900">No Assessment Pipelines Yet</h3>
              <p className="text-xs text-zinc-500 max-w-sm mx-auto">
                Create an assessment pipeline with custom DSA problems, take-home projects, and anti-cheating interview rounds.
              </p>
              <Button onClick={() => setIsCreateOpen(true)} className="text-xs">
                Create First Pipeline
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {pipelines.map((pipe) => (
                <Card key={pipe.id} className="p-6 space-y-5 rounded-2xl border-zinc-200 bg-white shadow-xs flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="font-bold text-base text-zinc-950">{pipe.title}</h2>
                        <p className="text-xs text-zinc-500">{pipe.target_role}</p>
                      </div>
                      <Badge variant="success" className="font-mono text-[10px]">
                        ACTIVE DRIVE
                      </Badge>
                    </div>

                    <p className="text-xs text-zinc-600 line-clamp-2 leading-relaxed">
                      {pipe.job_description}
                    </p>

                    {/* Configured Rounds */}
                    <div className="space-y-2 pt-1">
                      <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-400 font-bold">
                        Configured Stages:
                      </span>
                      <div className="space-y-1.5">
                        {pipe.rounds.map((r, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-2 rounded-xl bg-zinc-50 border border-zinc-200/80 text-xs"
                          >
                            <div className="flex items-center gap-2">
                              {r.round_type === 'oa_dsa' && <Code2 className="w-3.5 h-3.5 text-lime-600" />}
                              {r.round_type === 'ai_project' && <Boxes className="w-3.5 h-3.5 text-indigo-600" />}
                              {r.round_type === 'tough_interview' && <Mic className="w-3.5 h-3.5 text-amber-600" />}
                              {r.round_type === 'code_comprehension' && <Sparkles className="w-3.5 h-3.5 text-zinc-400" />}
                              <span className={r.is_enabled ? 'text-zinc-900 font-medium' : 'text-zinc-400'}>
                                {r.name}
                              </span>
                            </div>
                            <span className="text-[11px] font-mono text-zinc-500">
                              {r.time_limit_minutes}m
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Candidate Stats & Invite Actions */}
                  <div className="pt-4 border-t border-zinc-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs text-zinc-600 font-mono">
                      {pipe.candidates_count} Candidates Enrolled
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyInviteLink(pipe.invite_url, pipe.id)}
                        className="gap-1.5 text-xs bg-white border-zinc-200 hover:border-zinc-300"
                      >
                        {copiedId === pipe.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            <span className="text-emerald-700 font-bold">Copied Link</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Candidate Link</span>
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedPipelineId(pipe.id);
                          setIsInviteOpen(true);
                        }}
                        className="gap-1.5 text-xs bg-zinc-900 text-white hover:bg-zinc-800"
                      >
                        <Users className="w-3.5 h-3.5 text-lime-400" />
                        <span>Invite Candidate</span>
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Leaderboard & Telemetry */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-6">
          {/* Pipeline Selector */}
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold text-zinc-700">Drive:</label>
            <select
              value={selectedPipelineId || ''}
              onChange={(e) => setSelectedPipelineId(e.target.value)}
              className="text-xs px-3 py-1.5 rounded-xl border border-zinc-200 bg-white font-medium text-zinc-900 focus:outline-none focus:ring-1 focus:ring-lime-500"
            >
              {pipelines.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} ({p.target_role})
                </option>
              ))}
            </select>
          </div>

          {leaderboard ? (
            <Card className="border-zinc-200 rounded-2xl bg-white shadow-xs overflow-hidden">
              <div className="p-6 border-b border-zinc-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="font-bold text-base text-zinc-950">{leaderboard.pipeline_title}</h2>
                  <p className="text-xs text-zinc-500">
                    {leaderboard.total_candidates} Enrolled • {leaderboard.completed_candidates} Completed
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="px-3 py-1.5 rounded-xl bg-lime-50 border border-lime-200 text-xs font-mono font-bold text-lime-800">
                    Cohort Avg: {leaderboard.average_score != null ? `${leaderboard.average_score}%` : 'N/A'}
                  </div>
                </div>
              </div>

              {leaderboard.candidates.length === 0 ? (
                <div className="p-12 text-center text-xs text-zinc-400">
                  No candidates have enrolled or submitted answers yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-50 border-b border-zinc-200 font-mono text-zinc-500 uppercase text-[10px]">
                      <tr>
                        <th className="py-3 px-4">Rank</th>
                        <th className="py-3 px-4">Candidate</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Composite Score</th>
                        <th className="py-3 px-4">Integrity Signals</th>
                        <th className="py-3 px-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 font-sans">
                      {leaderboard.candidates.map((c) => {
                        const isFlagged = c.status === 'flagged';
                        const divergence = c.integrity_signals?.speech_code_divergence || 0;

                        return (
                          <tr key={c.id} className="hover:bg-zinc-50/70 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-zinc-400" title={c.rank == null ? 'Not ranked until finished and scored' : undefined}>
                              {c.rank != null ? `#${c.rank}` : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <p className="font-bold text-zinc-950">{c.candidate_name}</p>
                              <p className="text-[11px] text-zinc-500 font-mono">{c.candidate_email}</p>
                            </td>
                            <td className="py-3 px-4">
                              <Badge
                                variant={
                                  c.status === 'completed'
                                    ? 'success'
                                    : c.status === 'flagged'
                                    ? 'destructive'
                                    : 'outline'
                                }
                                className="text-[10px] capitalize font-mono"
                              >
                                {c.status}
                              </Badge>
                            </td>
                            <td className="py-3 px-4">
                              <span className="text-sm font-bold font-mono text-zinc-950">
                                {c.composite_score != null ? `${c.composite_score}%` : c.status === 'completed' ? 'Not scored' : 'In progress'}
                              </span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {(c.rounds || []).map((r: any, i: number) => {
                                  const res = c.round_results?.[String(i)];
                                  return (
                                    <span key={i} title={r.name} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 border border-zinc-200 text-zinc-600">
                                      R{i + 1} {res ? (res.score != null ? `${Math.round(res.score)}` : 'n/e') : '·'}
                                    </span>
                                  );
                                })}
                              </div>
                            </td>
                            <td className="py-3 px-4 space-y-1">
                              <div className="flex items-center gap-1.5">
                                {isFlagged ? (
                                  <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                                ) : (
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                )}
                                <span className={isFlagged ? 'text-rose-700 font-semibold' : 'text-zinc-600'}>
                                  {blurCount((c.integrity_signals as any)?.tab_switches_by_round ?? c.integrity_signals?.window_blurs)} tab switches
                                  {(c.integrity_signals as any)?.overtime_rounds?.length ? ` · ${(c.integrity_signals as any).overtime_rounds.length} overtime` : ''}
                                </span>
                              </div>
                              {divergence > 0.5 && (
                                <p className="text-[10px] text-amber-700 font-medium">
                                  Divergence Alert: High code speed vs verbal hesitation
                                </p>
                              )}
                            </td>
                            <td className="py-3 px-4 flex items-center gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setSelectedCandidateForAudit(c)}
                                className="text-[11px] gap-1 bg-white border-zinc-200 hover:border-zinc-300"
                              >
                                <FileText className="w-3 h-3 text-indigo-600" />
                                <span>Audit</span>
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => setReplayCandidate(c)}
                                className="text-[11px] gap-1 bg-white border-zinc-200 hover:border-zinc-300 text-lime-800"
                              >
                                <Activity className="w-3 h-3 text-lime-700" />
                                <span>Replay</span>
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          ) : (
            <div className="py-12 text-center text-xs text-zinc-400">
              Select a pipeline above to inspect candidates and integrity telemetry.
            </div>
          )}
        </div>
      )}

      {/* Modal: Candidate Deep Audit (Resume, Strengths/Weaknesses, Submitted Code) */}
      <Modal
        isOpen={Boolean(selectedCandidateForAudit)}
        onClose={() => setSelectedCandidateForAudit(null)}
        title={`Candidate Audit: ${selectedCandidateForAudit?.candidate_name || ''}`}
      >
        {selectedCandidateForAudit && (
          <div className="space-y-5 text-xs max-h-[75vh] overflow-y-auto pr-1">
            {/* Top Stat Bar */}
            <div className="grid grid-cols-3 gap-3 p-3 bg-zinc-50 rounded-xl border border-zinc-200">
              <div>
                <span className="text-[10px] uppercase font-mono text-zinc-400 font-bold">Composite Score</span>
                <p className="text-lg font-black text-lime-700">
                  {selectedCandidateForAudit.composite_score != null ? `${selectedCandidateForAudit.composite_score}%` : 'Not scored'}
                </p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-zinc-400 font-bold">Assessment Status</span>
                <p className="text-sm font-bold capitalize text-zinc-800">{selectedCandidateForAudit.status}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-zinc-400 font-bold">Focus Tab Switches</span>
                <p className={`text-sm font-bold ${blurCount((selectedCandidateForAudit.integrity_signals as any)?.tab_switches_by_round ?? selectedCandidateForAudit.integrity_signals?.window_blurs) > 2 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  {blurCount((selectedCandidateForAudit.integrity_signals as any)?.tab_switches_by_round ?? selectedCandidateForAudit.integrity_signals?.window_blurs)} Blurs
                </p>
              </div>
            </div>

            {/* Resume Text Section */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-zinc-900 flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-zinc-600" />
                Candidate Resume / Project Submissions
              </h4>
              <div className="p-3 bg-white rounded-xl border border-zinc-200 text-zinc-700 leading-relaxed font-sans max-h-32 overflow-y-auto">
                {selectedCandidateForAudit.resume_text || 'No resume text provided by candidate during intake.'}
              </div>
            </div>

            {/* Submitted Round 1 OA Code (Anti-Cheating Cross-Examination) */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-zinc-900 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-lime-700" />
                  Submitted Round 1 OA Code: {selectedCandidateForAudit.oa_problem_title || 'Algorithmic Challenge'}
                </h4>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setReplayCandidate(selectedCandidateForAudit)}
                  className="text-[11px] gap-1.5 h-7 px-2.5 bg-lime-50 text-lime-900 border-lime-300 hover:bg-lime-100"
                >
                  <Activity className="w-3.5 h-3.5 text-lime-700" />
                  <span>Launch Keystroke Replay</span>
                </Button>
              </div>
              <div className="p-3 bg-zinc-900 rounded-xl text-lime-400 font-mono text-xs overflow-x-auto max-h-48">
                <pre>{selectedCandidateForAudit.oa_submitted_code || selectedCandidateForAudit.round_results?.['0']?.submission?.code || '# No code recorded'}</pre>
              </div>
              <p className="text-[11px] text-zinc-500 italic">
                Cross-examination note: The Round 3 oral interviewer asks the candidate to explain their choice of data structure in this exact implementation.
              </p>
            </div>

            {/* Round Breakdown */}
            <div className="space-y-1.5">
              <h4 className="font-bold text-zinc-900">Multi-Round Performance Log</h4>
              <div className="space-y-2">
                {Object.entries(selectedCandidateForAudit.round_results || {}).map(([rIdx, rData]: [string, any]) => (
                  <div key={rIdx} className="p-3 rounded-xl bg-zinc-50 border border-zinc-200 flex flex-wrap items-center justify-between gap-y-2">
                    <div>
                      <span className="font-semibold text-zinc-900 uppercase font-mono text-[10px]">
                        Stage {Number(rIdx) + 1}: {rData.round_type}
                      </span>
                      <p className="text-[11px] text-zinc-500">
                        Submitted: {new Date(rData.submitted_at).toLocaleTimeString()}
                      </p>
                    </div>
                    <span className="font-bold font-mono text-lime-700 text-sm">
                      {rData.score != null ? `${rData.score}%` : 'Not evaluated'}
                    </span>
                    <RoundDetails data={rData} />
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-zinc-200 flex justify-end">
              <Button variant="outline" size="sm" onClick={() => setSelectedCandidateForAudit(null)}>
                Close Audit
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Modal: Create Assessment Pipeline with Custom OA Options */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Configure Hiring Assessment">
        <form onSubmit={handleCreatePipeline} className="space-y-4">
          <Input
            label="Assessment Drive Title"
            placeholder="e.g. Uber SDE-1 Campus Drive 2026"
            value={pipelineTitle}
            onChange={(e) => setPipelineTitle(e.target.value)}
            required
          />

          <Input
            label="Target Role & Level"
            placeholder="e.g. SDE-1 Backend / Systems Engineer"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            required
          />

          <div className="space-y-1">
            <label className="text-xs font-semibold text-zinc-800">Job Description &amp; Evaluation Focus</label>
            <textarea
              rows={3}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste Job Description requirements, key tech stacks, and grading expectations..."
              className="w-full px-3 py-2 rounded-xl border border-zinc-200 text-xs focus:ring-1 focus:ring-lime-500 focus:outline-none"
              required
            />
          </div>

          {/* Round sequence: every round is auto-graded on the server from curated, test-backed content */}
          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-zinc-800">Rounds (in order)</label>
            <p className="text-[11px] text-zinc-500">
              Candidates sign in with their own account. They never see scores; results land on your leaderboard.
            </p>
            {modelConnected === false && (
              <p className="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-2">
                No AI model is connected to your account. Coding and code-reading rounds are still graded, but the
                technical interview will show as "not evaluated". <a href="/settings/provider" className="underline font-semibold">Connect a model</a>.
              </p>
            )}
            <div className="space-y-2">
              {rounds.map((round, idx) => (
                <div key={round.round_type} className={`p-3 rounded-xl border text-xs space-y-2 ${round.is_enabled ? 'border-zinc-300 bg-white' : 'border-zinc-200 bg-zinc-50 opacity-70'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <label className="flex items-center gap-2 min-w-0">
                      <input
                        type="checkbox"
                        checked={round.is_enabled}
                        onChange={(e) => updateRound(idx, { is_enabled: e.target.checked })}
                        className="rounded text-lime-600 focus:ring-lime-500"
                      />
                      <input
                        value={round.name}
                        onChange={(e) => updateRound(idx, { name: e.target.value })}
                        aria-label="Round name"
                        className="font-semibold text-zinc-900 bg-transparent border-b border-transparent focus:border-zinc-300 focus:outline-none min-w-0 flex-1"
                      />
                    </label>
                    <div className="flex items-center gap-1 shrink-0">
                      <button type="button" aria-label="Move up" onClick={() => moveRound(idx, -1)} className="px-1.5 py-0.5 rounded border border-zinc-200 text-zinc-500 hover:text-zinc-900">↑</button>
                      <button type="button" aria-label="Move down" onClick={() => moveRound(idx, 1)} className="px-1.5 py-0.5 rounded border border-zinc-200 text-zinc-500 hover:text-zinc-900">↓</button>
                      <input
                        type="number"
                        min={10}
                        max={120}
                        value={round.time_limit_minutes}
                        onChange={(e) => updateRound(idx, { time_limit_minutes: Number(e.target.value) })}
                        aria-label="Time limit in minutes"
                        className="w-14 px-1.5 py-1 text-center font-mono border border-zinc-200 rounded-lg bg-white"
                      />
                      <span className="text-[11px] text-zinc-500">min</span>
                    </div>
                  </div>
                  {round.is_enabled && round.round_type === 'oa_dsa' && (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <select value={round.config?.difficulty} onChange={(e) => updateRound(idx, {}, { difficulty: e.target.value })}
                        className="text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Difficulty">
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="medium-hard">Medium to hard</option>
                        <option value="hard">Hard</option>
                      </select>
                      <select value={round.config?.problems_count} onChange={(e) => updateRound(idx, {}, { problems_count: Number(e.target.value) })}
                        className="text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Problem count">
                        {[1, 2, 3].map((n) => <option key={n} value={n}>{n} problem{n > 1 ? 's' : ''}</option>)}
                      </select>
                      <select value={(round.config?.problem_ids || [])[0] || ''} onChange={(e) => updateRound(idx, {}, { problem_ids: e.target.value ? [e.target.value] : [] })}
                        className="text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Fixed problem">
                        <option value="">Random per candidate</option>
                        {catalog.problems.map((p) => <option key={p.id} value={p.id}>{p.title} ({p.meta})</option>)}
                      </select>
                    </div>
                  )}
                  {round.is_enabled && round.round_type === 'code_comprehension' && (
                    <select value={round.config?.item_id || ''} onChange={(e) => updateRound(idx, {}, { item_id: e.target.value })}
                      className="w-full text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Code to read">
                      <option value="">Random codebase per candidate</option>
                      {catalog.items.map((i) => <option key={i.id} value={i.id}>{i.title} ({i.meta})</option>)}
                    </select>
                  )}
                  {round.is_enabled && round.round_type === 'ai_project' && (
                    <select value={round.config?.project_id} onChange={(e) => updateRound(idx, {}, { project_id: e.target.value })}
                      className="w-full text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Project">
                      {catalog.projects.map((p) => <option key={p.id} value={p.id}>{p.title} ({p.meta})</option>)}
                    </select>
                  )}
                  {round.is_enabled && round.round_type === 'tough_interview' && (
                    <select value={round.config?.questions_count} onChange={(e) => updateRound(idx, {}, { questions_count: Number(e.target.value) })}
                      className="w-full text-xs p-2 rounded-lg border border-zinc-200 bg-white" aria-label="Questions">
                      {[3, 4, 5, 6].map((n) => <option key={n} value={n}>{n} questions, adaptive follow-ups, cross-examines their code</option>)}
                    </select>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-zinc-900 text-white hover:bg-zinc-800">
              {isSubmitting ? 'Creating...' : 'Create Pipeline'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Invite Candidate */}
      <Modal isOpen={isInviteOpen} onClose={() => setIsInviteOpen(false)} title="Invite Candidate to Assessment">
        <form onSubmit={handleInviteCandidate} className="space-y-4">
          <Input
            label="Candidate Full Name"
            placeholder="e.g. John Doe"
            value={candidateName}
            onChange={(e) => setCandidateName(e.target.value)}
            required
          />

          <Input
            label="Candidate Email Address"
            type="email"
            placeholder="e.g. student@university.edu"
            value={candidateEmail}
            onChange={(e) => setCandidateEmail(e.target.value)}
            required
          />

          <div className="pt-4 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setIsInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isInviting} className="bg-zinc-900 text-white hover:bg-zinc-800">
              {isInviting ? 'Generating...' : 'Generate Candidate Link'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Recruiter Editor Telemetry Replay Modal */}
      {replayCandidate && (
        <EditorReplayModal
          isOpen={Boolean(replayCandidate)}
          onClose={() => setReplayCandidate(null)}
          candidateAssessmentId={replayCandidate.id}
          roundKey="0"
          candidateName={replayCandidate.candidate_name}
        />
      )}
    </div>
  );
};
