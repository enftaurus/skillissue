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
} from 'lucide-react';

export const EnterprisePortalPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'pipelines' | 'leaderboard'>('pipelines');
  const [pipelines, setPipelines] = useState<AssessmentPipeline[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<PipelineLeaderboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Candidate Audit Modal State
  const [selectedCandidateForAudit, setSelectedCandidateForAudit] = useState<CandidateAssessment | null>(null);

  // Create Pipeline Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [pipelineTitle, setPipelineTitle] = useState('');
  const [targetRole, setTargetRole] = useState('Software Development Engineer');
  const [jobDescription, setJobDescription] = useState('');
  const [oaMode, setOaMode] = useState<'preset' | 'custom_url' | 'codeforces_random'>('preset');
  const [oaCustomUrl, setOaCustomUrl] = useState('');
  const [oaCfRating, setOaCfRating] = useState(1500);
  const [oaCfTopic, setOaCfTopic] = useState('graphs');

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
        oa_config: {
          mode: oaMode,
          custom_url: oaMode === 'custom_url' ? oaCustomUrl : undefined,
          cf_rating: oaMode === 'codeforces_random' ? Number(oaCfRating) : undefined,
          cf_topic: oaMode === 'codeforces_random' ? oaCfTopic : undefined,
        },
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
                    Cohort Avg: {leaderboard.average_score}%
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
                      {leaderboard.candidates.map((c, index) => {
                        const isFlagged = c.status === 'flagged';
                        const divergence = c.integrity_signals?.speech_code_divergence || 0;

                        return (
                          <tr key={c.id} className="hover:bg-zinc-50/70 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-zinc-400">
                              #{index + 1}
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
                                {c.composite_score}%
                              </span>
                            </td>
                            <td className="py-3 px-4 space-y-1">
                              <div className="flex items-center gap-1.5">
                                {isFlagged ? (
                                  <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                                ) : (
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                )}
                                <span className={isFlagged ? 'text-rose-700 font-semibold' : 'text-zinc-600'}>
                                  {c.integrity_signals?.window_blurs || 0} Tab Switches
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
                                <span>Audit &amp; Code</span>
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => copyInviteLink(`/assess/take/${c.access_token}`, c.id)}
                                className="text-[11px] gap-1"
                              >
                                <Copy className="w-3 h-3" />
                                <span>Token</span>
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
                <p className="text-lg font-black text-lime-700">{selectedCandidateForAudit.composite_score}%</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-zinc-400 font-bold">Assessment Status</span>
                <p className="text-sm font-bold capitalize text-zinc-800">{selectedCandidateForAudit.status}</p>
              </div>
              <div>
                <span className="text-[10px] uppercase font-mono text-zinc-400 font-bold">Focus Tab Switches</span>
                <p className={`text-sm font-bold ${selectedCandidateForAudit.integrity_signals?.window_blurs > 2 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  {selectedCandidateForAudit.integrity_signals?.window_blurs || 0} Blurs
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
              <h4 className="font-bold text-zinc-900 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-lime-700" />
                Submitted Round 1 OA Code: {selectedCandidateForAudit.oa_problem_title || 'Algorithmic Challenge'}
              </h4>
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
                  <div key={rIdx} className="p-3 rounded-xl bg-zinc-50 border border-zinc-200 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-zinc-900 uppercase font-mono text-[10px]">
                        Stage {Number(rIdx) + 1}: {rData.round_type}
                      </span>
                      <p className="text-[11px] text-zinc-500">
                        Submitted: {new Date(rData.submitted_at).toLocaleTimeString()}
                      </p>
                    </div>
                    <span className="font-bold font-mono text-lime-700 text-sm">
                      {rData.score}%
                    </span>
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

          {/* OA Question Flexibility (Preset vs Custom URL vs Codeforces Randomizer) */}
          <div className="space-y-2 p-3 rounded-xl bg-zinc-50 border border-zinc-200">
            <label className="text-xs font-bold text-zinc-900 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-lime-600" />
              Round 1 OA Question Customization
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setOaMode('preset')}
                className={`p-2 rounded-lg text-xs font-medium border text-center transition-all ${
                  oaMode === 'preset'
                    ? 'bg-white border-lime-500 text-zinc-900 font-bold shadow-2xs'
                    : 'bg-zinc-100 border-zinc-200 text-zinc-600'
                }`}
              >
                Curated Preset
              </button>
              <button
                type="button"
                onClick={() => setOaMode('custom_url')}
                className={`p-2 rounded-lg text-xs font-medium border text-center transition-all ${
                  oaMode === 'custom_url'
                    ? 'bg-white border-lime-500 text-zinc-900 font-bold shadow-2xs'
                    : 'bg-zinc-100 border-zinc-200 text-zinc-600'
                }`}
              >
                Custom URL
              </button>
              <button
                type="button"
                onClick={() => setOaMode('codeforces_random')}
                className={`p-2 rounded-lg text-xs font-medium border text-center transition-all ${
                  oaMode === 'codeforces_random'
                    ? 'bg-white border-lime-500 text-zinc-900 font-bold shadow-2xs'
                    : 'bg-zinc-100 border-zinc-200 text-zinc-600'
                }`}
              >
                CF Randomizer
              </button>
            </div>

            {oaMode === 'custom_url' && (
              <Input
                label="Custom Problem URL"
                placeholder="https://leetcode.com/problems/... or codeforces.com/problemset/..."
                value={oaCustomUrl}
                onChange={(e) => setOaCustomUrl(e.target.value)}
              />
            )}

            {oaMode === 'codeforces_random' && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] font-semibold text-zinc-700">Difficulty Rating:</label>
                  <select
                    value={oaCfRating}
                    onChange={(e) => setOaCfRating(Number(e.target.value))}
                    className="w-full text-xs p-2 rounded-lg border border-zinc-200 bg-white"
                  >
                    <option value={1200}>1200 (Easy-Medium)</option>
                    <option value={1500}>1500 (Standard Interview)</option>
                    <option value={1800}>1800 (Hard FAANG Bar)</option>
                    <option value={2100}>2100 (Master / Uber Bar)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-zinc-700">Topic Domain:</label>
                  <select
                    value={oaCfTopic}
                    onChange={(e) => setOaCfTopic(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-zinc-200 bg-white"
                  >
                    <option value="graphs">Graphs &amp; Trees</option>
                    <option value="dp">Dynamic Programming</option>
                    <option value="data structures">Data Structures (Segment Trees, Heaps)</option>
                    <option value="greedy">Greedy &amp; Two Pointers</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Rounds Configurator */}
          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-zinc-800">Assessment Round Sequence:</label>
            <div className="space-y-2">
              {rounds.map((round, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 rounded-xl border border-zinc-200 bg-zinc-50 text-xs"
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
                      <span className="font-semibold text-zinc-900">{round.name}</span>
                      {round.round_type === 'code_comprehension' && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-zinc-200 text-zinc-700 font-mono">
                          Google-Style Beta
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
                      className="w-12 px-1.5 py-1 text-center font-mono border border-zinc-200 rounded-lg bg-white"
                    />
                    <span className="text-[11px] text-zinc-500">min</span>
                  </div>
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
    </div>
  );
};
