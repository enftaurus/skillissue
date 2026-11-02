import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { AssessmentPipeline, PipelineLeaderboard, RoundConfig } from '../../lib/types';
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
} from 'lucide-react';

export const EnterprisePortalPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pipelines' | 'leaderboard'>('pipelines');
  const [pipelines, setPipelines] = useState<AssessmentPipeline[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<PipelineLeaderboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Create Pipeline Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pipelineTitle, setPipelineTitle] = useState('');
  const [targetRole, setTargetRole] = useState('Software Development Engineer');
  const [jobDescription, setJobDescription] = useState('');
  const [rounds, setRounds] = useState<RoundConfig[]>([
    {
      round_type: 'oa_dsa',
      name: 'Round 1: Company DSA Online Assessment',
      time_limit_minutes: 35,
      is_enabled: true,
      config: { problems: 2, focus: 'Data Structures & Algorithms' },
    },
    {
      round_type: 'ai_project',
      name: 'Round 2: AI-Assisted Machine Coding (Take-Home Simulation)',
      time_limit_minutes: 30,
      is_enabled: true,
      config: { project: 'Distributed Rate Limiter', mode: 'read_only_copilot' },
    },
    {
      round_type: 'tough_interview',
      name: 'Round 3: Anti-Sycophancy Oral Technical Interview',
      time_limit_minutes: 20,
      is_enabled: true,
      config: { anti_sycophancy: true, speech_verification: true },
    },
    {
      round_type: 'code_comprehension',
      name: 'Round 4: Architecture & Code Comprehension (Google-Style)',
      time_limit_minutes: 20,
      is_enabled: false,
      config: { badge: 'Coming Soon' },
    },
  ]);
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
        rounds: rounds,
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="bg-white border border-surface-border rounded-xl p-6 sm:p-8 shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-500/10 border border-lime-500/20 text-lime-800 text-xs font-semibold">
            <Building2 className="w-3.5 h-3.5 text-lime-700" />
            Enterprise & Campus Placement Exam Portal
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">
            Recruitment Assessment Hub
          </h1>
          <p className="text-xs sm:text-sm text-ink-muted leading-relaxed">
            Configure automated multi-round candidate assessments: DSA coding, AI-assisted project take-home,
            and anti-sycophancy technical oral interviews with integrity signals.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => setIsCreateOpen(true)}
            className="gap-2 bg-ink text-white hover:bg-ink/90 text-xs font-semibold"
          >
            <Plus className="w-4 h-4 text-lime-400" />
            <span>New Hiring Assessment</span>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 text-xs font-medium">
        <button
          onClick={() => setActiveTab('pipelines')}
          className={`px-4 py-2 rounded-lg transition-all ${
            activeTab === 'pipelines'
              ? 'bg-surface-subtle text-ink font-bold border border-surface-border'
              : 'text-ink-muted hover:text-ink'
          }`}
        >
          Assessment Pipelines ({pipelines.length})
        </button>
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2 rounded-lg transition-all ${
            activeTab === 'leaderboard'
              ? 'bg-surface-subtle text-ink font-bold border border-surface-border'
              : 'text-ink-muted hover:text-ink'
          }`}
        >
          Candidate Leaderboard & Integrity
        </button>
      </div>

      {/* TAB 1: Pipelines */}
      {activeTab === 'pipelines' && (
        <div className="space-y-6">
          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-ink-muted">Loading pipelines...</p>
            </div>
          ) : pipelines.length === 0 ? (
            <Card className="p-12 text-center space-y-4">
              <Building2 className="w-12 h-12 text-ink-subtle mx-auto" />
              <h3 className="font-bold text-base text-ink">No Assessment Pipelines Yet</h3>
              <p className="text-xs text-ink-muted max-w-md mx-auto">
                Create your first hiring pipeline with custom rounds: OA, AI Machine Coding, and Oral Interview.
              </p>
              <Button onClick={() => setIsCreateOpen(true)} className="gap-2 text-xs">
                <Plus className="w-4 h-4" />
                <span>Create Assessment Pipeline</span>
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {pipelines.map((pipe) => (
                <Card key={pipe.id} className="p-6 space-y-5 hover:shadow-card-hover transition-all">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-base text-ink">{pipe.title}</h3>
                      <p className="text-xs text-ink-muted font-mono">{pipe.target_role}</p>
                    </div>
                    <Badge variant={pipe.is_active ? 'success' : 'outline'} className="text-[10px]">
                      {pipe.is_active ? 'Active Drive' : 'Closed'}
                    </Badge>
                  </div>

                  {/* Configured Rounds */}
                  <div className="space-y-2">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-ink-subtle">
                      Configured Multi-Round Stages:
                    </span>
                    <div className="space-y-1.5">
                      {pipe.rounds.map((r, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-lg bg-surface-subtle border border-surface-border text-xs"
                        >
                          <div className="flex items-center gap-2">
                            {r.round_type === 'oa_dsa' && <Code2 className="w-3.5 h-3.5 text-lime-600" />}
                            {r.round_type === 'ai_project' && <Boxes className="w-3.5 h-3.5 text-indigo-600" />}
                            {r.round_type === 'tough_interview' && <Mic className="w-3.5 h-3.5 text-amber-600" />}
                            {r.round_type === 'code_comprehension' && <Sparkles className="w-3.5 h-3.5 text-slate-400" />}
                            <span className={r.is_enabled ? 'text-ink font-medium' : 'text-ink-subtle'}>
                              {r.name}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-ink-subtle">
                            {r.time_limit_minutes}m
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Candidate Stats & Invite Actions */}
                  <div className="pt-3 border-t border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <span className="text-xs text-ink-muted font-mono">
                      {pipe.candidates_count} Candidates Enrolled
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyInviteLink(pipe.invite_url, pipe.id)}
                        className="gap-1.5 text-xs"
                      >
                        {copiedId === pipe.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            <span className="text-emerald-700">Copied Link</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Exam Link</span>
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedPipelineId(pipe.id);
                          setIsInviteOpen(true);
                        }}
                        className="gap-1.5 text-xs bg-ink text-white hover:bg-ink/90"
                      >
                        <Users className="w-3.5 h-3.5" />
                        <span>Invite</span>
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Leaderboard & Integrity Telemetry */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-6">
          {/* Pipeline Selector */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-ink-muted">Select Pipeline:</span>
            <select
              value={selectedPipelineId || ''}
              onChange={(e) => setSelectedPipelineId(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-surface-border bg-white text-xs font-medium text-ink focus:outline-none focus:ring-1 focus:ring-lime-500"
            >
              {pipelines.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
          </div>

          {leaderboard ? (
            <Card className="overflow-hidden border border-surface-border">
              <div className="p-5 border-b border-surface-border bg-surface-subtle/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-base text-ink">{leaderboard.pipeline_title}</h3>
                  <p className="text-xs text-ink-muted">
                    {leaderboard.completed_candidates} of {leaderboard.total_candidates} completed all rounds
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-white border border-surface-border">
                    <span className="text-ink-subtle">Average Score: </span>
                    <span className="font-bold text-ink">{leaderboard.average_score}%</span>
                  </div>
                </div>
              </div>

              {leaderboard.candidates.length === 0 ? (
                <div className="p-12 text-center text-xs text-ink-muted">
                  No candidates have enrolled or submitted answers yet.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-surface-subtle border-b border-surface-border font-mono text-ink-subtle uppercase text-[10px]">
                      <tr>
                        <th className="py-3 px-4">Rank</th>
                        <th className="py-3 px-4">Candidate</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Composite Score</th>
                        <th className="py-3 px-4">Integrity Signals</th>
                        <th className="py-3 px-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border font-sans">
                      {leaderboard.candidates.map((c, index) => {
                        const isFlagged = c.status === 'flagged';
                        const divergence = c.integrity_signals?.speech_code_divergence || 0;

                        return (
                          <tr key={c.id} className="hover:bg-surface-subtle/40 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-ink-muted">
                              #{index + 1}
                            </td>
                            <td className="py-3 px-4">
                              <p className="font-bold text-ink">{c.candidate_name}</p>
                              <p className="text-[11px] text-ink-muted font-mono">{c.candidate_email}</p>
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
                                className="text-[10px] capitalize"
                              >
                                {c.status}
                              </Badge>
                            </td>
                            <td className="py-3 px-4">
                              <span className="text-sm font-bold font-mono text-ink">
                                {c.composite_score}%
                              </span>
                            </td>
                            <td className="py-3 px-4 space-y-1">
                              <div className="flex items-center gap-1.5">
                                {isFlagged ? (
                                  <ShieldAlert className="w-3.5 h-3.5 text-red-600" />
                                ) : (
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                )}
                                <span className={isFlagged ? 'text-red-700 font-semibold' : 'text-ink-muted'}>
                                  {c.integrity_signals?.window_blurs || 0} Tab Switches
                                </span>
                              </div>
                              {divergence > 0.5 && (
                                <p className="text-[10px] text-amber-700 font-medium">
                                  Divergence Alert: High code speed vs verbal hesitation
                                </p>
                              )}
                            </td>
                            <td className="py-3 px-4">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => copyInviteLink(`/assess/take/${c.access_token}`, c.id)}
                                className="text-[11px] gap-1"
                              >
                                <Copy className="w-3 h-3" />
                                <span>Exam Token</span>
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
            <div className="py-12 text-center text-xs text-ink-muted">
              Select a pipeline above to inspect candidates and integrity telemetry.
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Assessment Pipeline */}
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
            placeholder="e.g. SDE-1 Backend / Intern"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            required
          />

          <div className="space-y-1">
            <label className="text-xs font-semibold text-ink">Job Description & Evaluation Focus</label>
            <textarea
              rows={4}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste Job Description requirements, key tech stacks, and grading expectations..."
              className="w-full px-3 py-2 rounded-lg border border-surface-border text-xs focus:ring-1 focus:ring-lime-500 focus:outline-none"
              required
            />
          </div>

          {/* Rounds Configurator */}
          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-ink">Assessment Round Sequence:</label>
            <div className="space-y-2">
              {rounds.map((round, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-lg border border-surface-border bg-surface-subtle text-xs"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={round.is_enabled}
                      disabled={round.round_type === 'code_comprehension'}
                      onChange={(e) => {
                        const next = [...rounds];
                        next[idx].is_enabled = e.target.checked;
                        setRounds(next);
                      }}
                      className="rounded text-lime-600 focus:ring-lime-500"
                    />
                    <div>
                      <span className="font-semibold text-ink">{round.name}</span>
                      {round.round_type === 'code_comprehension' && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 font-mono">
                          Coming Soon (Google-Style)
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      min={10}
                      max={90}
                      value={round.time_limit_minutes}
                      onChange={(e) => {
                        const next = [...rounds];
                        next[idx].time_limit_minutes = Number(e.target.value);
                        setRounds(next);
                      }}
                      className="w-12 px-1.5 py-1 text-center font-mono border border-surface-border rounded bg-white"
                    />
                    <span className="text-[11px] text-ink-muted">min</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="bg-ink text-white hover:bg-ink/90">
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
            <Button type="submit" disabled={isInviting} className="bg-ink text-white hover:bg-ink/90">
              {isInviting ? 'Generating...' : 'Generate Candidate Link'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
