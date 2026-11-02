import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { CompanyTrackDetail } from '../../lib/types';
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
} from 'lucide-react';

export const CompanyTrackDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [track, setTrack] = useState<CompanyTrackDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
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

      {/* Problems List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-ink flex items-center gap-2">
            <Code2 className="w-4 h-4 text-lime-600" />
            <span>High-Frequency Interview Problems</span>
          </h2>
          <span className="text-xs text-ink-muted font-mono">
            First 3 Unlocked on Day-1
          </span>
        </div>

        <div className="space-y-3">
          {track.problems.map((problem) => {
            const isDay1 = problem.order_index <= 3;

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
                            {problem.topics.slice(0, 3).join(', ')}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {problem.is_unlocked ? (
                      <Button
                        size="sm"
                        onClick={() => navigate('/coding')}
                        className="gap-1.5 text-xs bg-ink text-white hover:bg-ink/90 font-medium"
                      >
                        <Code2 className="w-3.5 h-3.5" />
                        <span>Solve in Arena</span>
                      </Button>
                    ) : (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-subtle text-ink-muted text-xs font-mono border border-surface-border">
                        <Lock className="w-3.5 h-3.5 text-ink-subtle" />
                        <span>Locked</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
