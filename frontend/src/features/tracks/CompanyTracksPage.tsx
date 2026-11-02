import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { CompanyTrackSummary } from '../../lib/types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import {
  Building2,
  Car,
  Search,
  Package,
  Layers,
  Share2,
  FileText,
  Compass,
  Utensils,
  Award,
  Sparkles,
  Unlock,
  ArrowRight,
  Flame,
  Zap,
} from 'lucide-react';

const ICON_MAP: Record<string, React.ElementType> = {
  Car,
  Search,
  Package,
  Layers,
  Share2,
  FileText,
  Compass,
  Utensils,
  Award,
  Building2,
};

export const CompanyTracksPage: React.FC = () => {
  const [tracks, setTracks] = useState<CompanyTrackSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<'all' | 'gold' | 'silver' | 'bronze'>('all');
  const navigate = useNavigate();

  useEffect(() => {
    api.get<CompanyTrackSummary[]>('/tracks/companies')
      .then(setTracks)
      .catch((err) => console.error('Failed to load company tracks', err))
      .finally(() => setLoading(false));
  }, []);

  const filteredTracks = selectedTier === 'all'
    ? tracks
    : tracks.filter((t) => t.tier === selectedTier);

  const goldTracks = tracks.filter((t) => t.tier === 'gold');
  const silverTracks = tracks.filter((t) => t.tier === 'silver');
  const bronzeTracks = tracks.filter((t) => t.tier === 'bronze');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Hero Banner */}
      <div className="bg-white border border-surface-border rounded-xl p-6 sm:p-8 relative overflow-hidden shadow-card">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-500/10 border border-lime-500/20 text-lime-800 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-lime-700" />
            Curated from Community Experiences (Reddit & LeetCode Discuss)
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-ink">
            Company Career Tracks & Placement Packs
          </h1>
          <p className="text-sm sm:text-base text-ink-muted leading-relaxed">
            Target company-specific interview loops with realistic algorithmic problem sets and community debriefs.
            Every company features <span className="font-semibold text-ink">2–3 flagship problems unlocked on Day 1</span>.
            Solve problems and complete mock interviews to progressively unlock the remaining question pool.
          </p>
        </div>

        {/* Quick Stats Pill */}
        <div className="mt-6 pt-6 border-t border-surface-border grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-ink-subtle uppercase tracking-wider font-mono">Gold Mine</span>
            <p className="text-base font-bold text-amber-600 mt-0.5">{goldTracks.length} Tech Giants</p>
          </div>
          <div>
            <span className="text-ink-subtle uppercase tracking-wider font-mono">Silver Mine</span>
            <p className="text-base font-bold text-slate-700 mt-0.5">{silverTracks.length} Tier-2 Firms</p>
          </div>
          <div>
            <span className="text-ink-subtle uppercase tracking-wider font-mono">Bronze Mine</span>
            <p className="text-base font-bold text-amber-800 mt-0.5">{bronzeTracks.length} High-Growth / Campus</p>
          </div>
          <div>
            <span className="text-ink-subtle uppercase tracking-wider font-mono">Day-1 Open</span>
            <p className="text-base font-bold text-lime-600 mt-0.5">3 Questions / Company</p>
          </div>
        </div>
      </div>

      {/* Tier Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 p-1 bg-surface-subtle border border-surface-border rounded-lg text-xs font-medium">
          <button
            onClick={() => setSelectedTier('all')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              selectedTier === 'all'
                ? 'bg-white text-ink shadow-sm font-semibold'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            All Tracks ({tracks.length})
          </button>
          <button
            onClick={() => setSelectedTier('gold')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              selectedTier === 'gold'
                ? 'bg-amber-500/10 text-amber-800 border border-amber-500/20 font-semibold'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-amber-600" />
            Gold Mine ({goldTracks.length})
          </button>
          <button
            onClick={() => setSelectedTier('silver')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              selectedTier === 'silver'
                ? 'bg-slate-200 text-slate-800 font-semibold'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            <Zap className="w-3.5 h-3.5 text-slate-600" />
            Silver Mine ({silverTracks.length})
          </button>
          <button
            onClick={() => setSelectedTier('bronze')}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              selectedTier === 'bronze'
                ? 'bg-amber-700/10 text-amber-900 border border-amber-700/20 font-semibold'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            <Award className="w-3.5 h-3.5 text-amber-700" />
            Bronze Mine ({bronzeTracks.length})
          </button>
        </div>

        <div className="text-xs text-ink-subtle flex items-center gap-2 font-mono">
          <Unlock className="w-3.5 h-3.5 text-lime-600" />
          <span>Practice to unlock locked problems</span>
        </div>
      </div>

      {/* Grid of Company Cards */}
      {loading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-ink-muted">Loading community company tracks...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTracks.map((track) => {
            const Icon = ICON_MAP[track.logo_icon] || Building2;
            const unlockPct = Math.round((track.unlocked_count / Math.max(1, track.total_problems)) * 100);

            const tierStyle =
              track.tier === 'gold'
                ? 'border-amber-500/30 bg-gradient-to-br from-amber-50/20 to-white'
                : track.tier === 'silver'
                ? 'border-slate-300 bg-gradient-to-br from-slate-50/20 to-white'
                : 'border-amber-700/20 bg-gradient-to-br from-orange-50/20 to-white';

            return (
              <Card
                key={track.id}
                className={`flex flex-col justify-between hover:shadow-card-hover transition-all duration-200 border ${tierStyle}`}
              >
                <div className="p-6 space-y-4">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-center text-ink">
                        <Icon className="w-5 h-5 text-ink" />
                      </div>
                      <div>
                        <h3 className="font-bold text-base text-ink flex items-center gap-2">
                          {track.name}
                        </h3>
                        <p className="text-xs text-ink-muted">{track.role_title}</p>
                      </div>
                    </div>
                    <Badge
                      variant={track.tier === 'gold' ? 'warning' : 'outline'}
                      className="capitalize font-mono text-[10px]"
                    >
                      {track.tier} Mine
                    </Badge>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-ink-muted line-clamp-2 leading-relaxed">
                    {track.description}
                  </p>

                  {/* Community Insight Callout */}
                  {track.community_tips && track.community_tips.length > 0 && (
                    <div className="bg-surface-subtle/80 rounded-lg p-3 border border-surface-border text-[11px] space-y-1">
                      <span className="font-semibold text-ink flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-ink-subtle">
                        <Sparkles className="w-3 h-3 text-lime-600" />
                        Community Debrief Tip
                      </span>
                      <p className="text-ink-muted italic line-clamp-2">
                        &ldquo;{track.community_tips[0]}&rdquo;
                      </p>
                    </div>
                  )}

                  {/* Unlock Progress Bar */}
                  <div className="space-y-1.5 pt-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-ink-muted flex items-center gap-1">
                        <Unlock className="w-3 h-3 text-lime-600" />
                        {track.unlocked_count} of {track.total_problems} Unlocked
                      </span>
                      <span className="font-mono text-ink-subtle">{unlockPct}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-surface-subtle rounded-full overflow-hidden border border-surface-border">
                      <div
                        className="h-full bg-lime-500 rounded-full transition-all duration-300"
                        style={{ width: `${unlockPct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Card Action Footer */}
                <div className="px-6 py-3.5 bg-surface-subtle/40 border-t border-surface-border flex items-center justify-between">
                  <span className="text-[11px] text-ink-subtle font-mono">
                    3 Open Day-1
                  </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(`/tracks/${track.slug}`)}
                    className="gap-1.5 text-xs group"
                  >
                    <span>View Track</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
