import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { CompanyTrackDetail, ToggleProblemSolvedResponse } from '../../lib/types';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  Building2,
  Lock,
  CheckCircle2,
  Code2,
  Mic,
  ArrowLeft,
  Sparkles,
  ExternalLink,
  Search,
} from 'lucide-react';

export const CompanyTrackDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [track, setTrack] = useState<CompanyTrackDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'ALL' | 'UNLOCKED' | 'SOLVED' | 'EASY' | 'MEDIUM' | 'HARD'>('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;
  const navigate = useNavigate();

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    setCurrentPage(1);
    api.get<CompanyTrackDetail>(`/tracks/companies/${slug}`)
      .then(setTrack)
      .catch((err) => {
        console.error('Failed to load track details', err);
        setError('Could not load company track.');
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const handleStartMockInterview = async () => {
    if (!track) return;
    try {
      // Create targeted interview for this company
      const res = await api.post<any>('/interviews/domain', {
        category: 'technical',
        domain_skills: [track.name, 'System Design', 'Algorithms', 'Concurrency'],
        target_role: track.role_title,
        difficulty: track.tier === 'gold' ? 'hard' : 'intermediate',
      });
      navigate(`/interviews/${res.id}`);
    } catch (err) {
      console.error('Failed to launch company mock interview', err);
    }
  };

  const handleToggleSolved = async (problemId: string) => {
    setTogglingId(problemId);
    try {
      const res = await api.post<ToggleProblemSolvedResponse>(`/tracks/problems/${problemId}/toggle-solved`);
      setTrack((prev) => {
        if (!prev) return prev;
        const updatedProblems = prev.problems.map((p) => {
          if (p.id === problemId) {
            return { ...p, is_solved: res.is_solved };
          }
          if (p.order_index <= res.unlocked_count) {
            return { ...p, is_unlocked: true };
          }
          return p;
        });
        return {
          ...prev,
          solved_count: res.solved_count,
          unlocked_count: res.unlocked_count,
          problems: updatedProblems,
        };
      });

      if (res.unlocked_new_problem && res.new_unlocked_problem_title) {
        setToastMessage(`Question completed! Unlocked: "${res.new_unlocked_problem_title}" on LeetCode.`);
        setTimeout(() => setToastMessage(null), 5000);
      }
    } catch (err) {
      console.error('Failed to toggle problem status', err);
    } finally {
      setTogglingId(null);
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs text-ink-muted">Loading company track...</p>
      </div>
    );
  }

  if (error || !track) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 text-center space-y-4">
        <p className="text-sm text-red-600">{error || 'Track not found.'}</p>
        <Button variant="outline" onClick={() => navigate('/tracks')}>
          Back to Career Tracks
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Back button */}
      <div>
        <Link
          to="/tracks"
          className="inline-flex items-center gap-2 text-xs font-medium text-ink-muted hover:text-ink transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to All Company Tracks</span>
        </Link>
      </div>

      {/* Track Header Card */}
      <div className="bg-white border border-surface-border rounded-xl p-6 sm:p-8 space-y-6 shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-lg bg-surface-subtle border border-surface-border">
                <Building2 className="w-6 h-6 text-ink" />
              </span>
              <div>
                <h1 className="text-2xl font-bold text-ink">{track.name} Career Track</h1>
                <p className="text-xs text-ink-muted">{track.role_title}</p>
              </div>
              <Badge
                variant={track.tier === 'gold' ? 'warning' : 'outline'}
                className="capitalize font-mono text-[10px] ml-2"
              >
                {track.tier} Mine
              </Badge>
            </div>
            <p className="text-sm text-ink-muted leading-relaxed">
              {track.description}
            </p>
          </div>

          {/* Action Button: Start Mock Interview */}
          <div className="flex-shrink-0">
            <Button
              onClick={handleStartMockInterview}
              className="w-full sm:w-auto gap-2 bg-ink text-white hover:bg-ink/90 text-xs font-semibold"
            >
              <Mic className="w-4 h-4 text-lime-400" />
              <span>Start {track.name} AI Mock Interview</span>
            </Button>
          </div>
        </div>

        {/* Community Debrief Box */}
        {track.community_tips && track.community_tips.length > 0 && (
          <div className="bg-lime-50/50 border border-lime-500/20 rounded-xl p-5 space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-lime-900 uppercase tracking-wider">
              <Sparkles className="w-4 h-4 text-lime-700" />
              <span>Crowdsourced Community Debriefs (Reddit & LeetCode Discuss)</span>
            </div>
            <ul className="space-y-2 text-xs text-lime-950">
              {track.community_tips.map((tip, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-lime-600 font-bold">•</span>
                  <span className="leading-relaxed">&ldquo;{tip}&rdquo;</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Unlock Tracker Bar */}
        <div className="bg-surface-subtle/50 rounded-xl p-4 border border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-lime-500/10 border border-lime-500/20 flex items-center justify-center text-lime-700 font-bold font-mono">
              {track.unlocked_count}
            </div>
            <div>
              <p className="font-semibold text-ink">
                {track.unlocked_count} of {track.total_problems} Problems Available
              </p>
              <p className="text-[11px] text-ink-muted">
                Solve unlocked questions to automatically open the next question in the pool.
              </p>
            </div>
          </div>
          <span className="text-[11px] font-mono text-ink-subtle">
            {track.solved_count} Solved
          </span>
        </div>
      </div>

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center justify-between shadow-xs animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      {(() => {
        const allProblems = track.problems || [];
        const filteredProblems = allProblems.filter((p) => {
          const q = searchQuery.trim().toLowerCase();
          const matchesQuery =
            !q ||
            p.title.toLowerCase().includes(q) ||
            p.slug.toLowerCase().includes(q) ||
            (p.topics && p.topics.some((t) => t.toLowerCase().includes(q)));

          if (!matchesQuery) return false;
          if (filterMode === 'UNLOCKED') return p.is_unlocked;
          if (filterMode === 'SOLVED') return p.is_solved;
          if (filterMode === 'EASY') return p.difficulty === 'EASY';
          if (filterMode === 'MEDIUM') return p.difficulty === 'MEDIUM';
          if (filterMode === 'HARD') return p.difficulty === 'HARD';
          return true;
        });

        const totalPages = Math.ceil(filteredProblems.length / pageSize) || 1;
        const safePage = Math.min(currentPage, totalPages);
        const startIndex = (safePage - 1) * pageSize;
        const currentSlice = filteredProblems.slice(startIndex, startIndex + pageSize);

        return (
          <div className="space-y-4">
            {/* Search & Filter Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-ink flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-lime-600" />
                  <span>High-Frequency Interview Problems ({allProblems.length} Curated)</span>
                </h2>
                <p className="text-xs text-ink-muted">
                  First 3 unlocked on Day 1. Complete unlocked questions to open the next in the sequence.
                </p>
              </div>

              {/* Search input */}
              <div className="relative w-full md:w-72">
                <Search className="w-3.5 h-3.5 text-ink-muted absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Search by title, topic, or slug..."
                  className="w-full pl-9 pr-8 py-2 text-xs rounded-xl border border-surface-border bg-white text-ink placeholder:text-ink-muted focus:outline-none focus:ring-2 focus:ring-lime-500/20 focus:border-lime-500"
                />
                {searchQuery && (
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setCurrentPage(1);
                    }}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-ink-muted hover:text-ink"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-2 flex-wrap text-xs">
              {(
                [
                  { id: 'ALL', label: `All (${allProblems.length})` },
                  { id: 'UNLOCKED', label: `Unlocked (${allProblems.filter((p) => p.is_unlocked).length})` },
                  { id: 'SOLVED', label: `Solved (${track.solved_count})` },
                  { id: 'EASY', label: 'Easy' },
                  { id: 'MEDIUM', label: 'Medium' },
                  { id: 'HARD', label: 'Hard' },
                ] as const
              ).map((f) => (
                <button
                  key={f.id}
                  onClick={() => {
                    setFilterMode(f.id);
                    setCurrentPage(1);
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    filterMode === f.id
                      ? 'bg-ink text-white shadow-xs'
                      : 'bg-surface-subtle text-ink-muted hover:text-ink border border-surface-border'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Problem count readout */}
            <div className="flex items-center justify-between text-xs text-ink-muted font-mono pt-1">
              <span>
                Showing {filteredProblems.length === 0 ? 0 : startIndex + 1}–
                {Math.min(startIndex + pageSize, filteredProblems.length)} of {filteredProblems.length} problems
              </span>
              <span>
                Page {safePage} of {totalPages}
              </span>
            </div>

            {/* Problems Cards */}
            <div className="space-y-3">
              {currentSlice.length === 0 ? (
                <div className="p-8 text-center rounded-xl border border-surface-border bg-white text-xs text-ink-muted space-y-2">
                  <p className="font-semibold text-ink">No problems matched your query.</p>
                  <p>Try clearing your search term or selecting &ldquo;All&rdquo; filter.</p>
                </div>
              ) : (
                currentSlice.map((problem) => {
                  const isDay1 = problem.order_index <= 3;
                  const leetcodeLink = problem.leetcode_url || `https://leetcode.com/problems/${problem.slug}/`;

                  return (
                    <div
                      key={problem.id}
                      className={`p-4 sm:p-5 rounded-xl border transition-all ${
                        problem.is_unlocked
                          ? 'bg-white border-surface-border hover:shadow-card hover:border-lime-500/40'
                          : 'bg-surface-subtle/50 border-surface-border/60 opacity-70'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="text-xs font-mono font-bold text-ink-muted">
                              #{problem.order_index}
                            </span>
                            <h3 className="font-bold text-sm text-ink">
                              {problem.title}
                            </h3>
                            <Badge
                              variant={
                                problem.difficulty === 'HARD'
                                  ? 'destructive'
                                  : problem.difficulty === 'MEDIUM'
                                  ? 'warning'
                                  : 'success'
                              }
                              className="text-[10px] font-mono"
                            >
                              {problem.difficulty}
                            </Badge>
                            {isDay1 && (
                              <span className="px-2 py-0.5 rounded-full bg-lime-500/10 text-lime-800 text-[10px] font-semibold border border-lime-500/20">
                                Day 1 Open
                              </span>
                            )}
                            {problem.is_solved && (
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 text-[10px] font-semibold flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                Solved
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2 flex-wrap text-[11px] text-ink-muted">
                            <span>Frequency: {Math.round(problem.frequency_score)}%</span>
                            <span>•</span>
                            <span>Acceptance: {Math.round(problem.acceptance_rate * 100)}%</span>
                            {problem.topics && problem.topics.length > 0 && (
                              <>
                                <span>•</span>
                                <span className="text-ink-subtle">
                                  {problem.topics.slice(0, 4).join(', ')}
                                </span>
                              </>
                            )}
                          </div>

                          {/* Direct LeetCode URL */}
                          <div className="flex items-center gap-1.5 pt-0.5 flex-wrap">
                            <span className="text-[11px] font-semibold text-zinc-500">LeetCode Link:</span>
                            <a
                              href={leetcodeLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 text-[11px] font-mono text-lime-700 hover:text-lime-850 hover:underline"
                            >
                              <span>{leetcodeLink}</span>
                              <ExternalLink className="w-2.5 h-2.5 text-lime-600" />
                            </a>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          {problem.is_unlocked ? (
                            <div className="flex items-center gap-2">
                              <a
                                href={leetcodeLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 text-white hover:bg-zinc-800 text-xs font-semibold shadow-xs transition-colors"
                              >
                                <ExternalLink className="w-3.5 h-3.5 text-lime-400" />
                                <span>Solve on LeetCode</span>
                              </a>

                              <Button
                                size="sm"
                                disabled={togglingId === problem.id}
                                onClick={() => handleToggleSolved(problem.id)}
                                className={`gap-1.5 text-xs font-medium border ${
                                  problem.is_solved
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100'
                                    : 'bg-white text-zinc-800 border-zinc-200 hover:bg-zinc-50'
                                }`}
                              >
                                <CheckCircle2
                                  className={`w-3.5 h-3.5 ${problem.is_solved ? 'text-emerald-600' : 'text-zinc-400'}`}
                                />
                                <span>{problem.is_solved ? 'Solved' : 'Mark Solved'}</span>
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-subtle text-ink-muted text-xs font-mono border border-surface-border">
                              <Lock className="w-3.5 h-3.5 text-ink-subtle" />
                              <span>Locked (Complete #{problem.order_index - 1} to unlock)</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t border-surface-border">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage <= 1}
                  onClick={() => {
                    setCurrentPage((prev) => Math.max(1, prev - 1));
                    window.scrollTo({ top: 300, behavior: 'smooth' });
                  }}
                  className="text-xs"
                >
                  Previous Page
                </Button>

                <div className="flex items-center gap-1">
                  <span className="text-xs text-ink-muted font-mono">
                    Page {safePage} of {totalPages}
                  </span>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage >= totalPages}
                  onClick={() => {
                    setCurrentPage((prev) => Math.min(totalPages, prev + 1));
                    window.scrollTo({ top: 300, behavior: 'smooth' });
                  }}
                  className="text-xs"
                >
                  Next Page
                </Button>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
};

