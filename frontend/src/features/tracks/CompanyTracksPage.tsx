import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../lib/api';
import { CompanyTrackSummary, PresetSimulation } from '../../lib/types';
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
  Play,
  Clock,
  ShieldCheck,
  Code2,
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
  Sparkles,
};

export const CompanyTracksPage: React.FC = () => {
  const [tracks, setTracks] = useState<CompanyTrackSummary[]>([]);
  const [simulations, setSimulations] = useState<PresetSimulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMainTab, setActiveMainTab] = useState<'packs' | 'simulations' | 'comprehension'>('packs');
  const [selectedTier, setSelectedTier] = useState<'all' | 'gold' | 'silver' | 'bronze'>('all');
  const navigate = useNavigate();
  const [startingSim, setStartingSim] = useState<string | null>(null);
  const [simError, setSimError] = useState('');

  const startSimulation = async (simId: string) => {
    setStartingSim(simId);
    setSimError('');
    try {
      const res = await api.post<{ access_token: string }>(`/tracks/simulations/${simId}/start`, {});
      navigate(`/assess/take/${res.access_token}`);
    } catch (e: any) {
      setSimError(e?.message || 'Could not start the simulation.');
    } finally {
      setStartingSim(null);
    }
  };

  useEffect(() => {
    Promise.all([
      api.get<CompanyTrackSummary[]>('/tracks/companies').catch(() => []),
      api.get<PresetSimulation[]>('/tracks/simulations').catch(() => []),
    ])
      .then(([tracksData, simsData]) => {
        setTracks(tracksData);
        setSimulations(simsData);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredTracks = selectedTier === 'all'
    ? tracks
    : tracks.filter((t) => t.tier === selectedTier);

  const goldTracks = tracks.filter((t) => t.tier === 'gold');
  const silverTracks = tracks.filter((t) => t.tier === 'silver');
  const bronzeTracks = tracks.filter((t) => t.tier === 'bronze');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in bg-zinc-50/30 min-h-screen">
      {/* Hero Banner */}
      <div className="bg-white border border-zinc-200 rounded-2xl p-6 sm:p-8 relative overflow-hidden shadow-xs">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-lime-50 border border-lime-200 text-lime-800 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-lime-700" />
            Curated from candidate experiences gathered from community platforms (LeetCode Discuss, Reddit, Glassdoor)
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-zinc-950">
            Company Career Tracks &amp; Placement Simulations
          </h1>
          <p className="text-sm sm:text-base text-zinc-600 leading-relaxed">
            Practice realistic company question pools across <span className="font-semibold text-zinc-900">50+ top tech companies</span> or sit a full, timed hiring simulation for Google, Uber or OpenAI: every round is graded on real tests, and you get the full report at the end.
            Every pack features <span className="font-semibold text-zinc-900">2–3 questions unlocked on Day 1</span>.
          </p>
        </div>

        {/* Quick Stats Pill */}
        <div className="mt-6 pt-6 border-t border-zinc-100 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div>
            <span className="text-zinc-500 uppercase tracking-wider font-mono">Gold Tech Giants</span>
            <p className="text-base font-bold text-amber-600 mt-0.5">{goldTracks.length || 12} Companies</p>
          </div>
          <div>
            <span className="text-zinc-500 uppercase tracking-wider font-mono">Silver &amp; Bronze</span>
            <p className="text-base font-bold text-zinc-700 mt-0.5">{(silverTracks.length + bronzeTracks.length) || 40} High Growth</p>
          </div>
          <div>
            <span className="text-zinc-500 uppercase tracking-wider font-mono">Placement Simulations</span>
            <p className="text-base font-bold text-indigo-600 mt-0.5">Google • Uber • OpenAI</p>
          </div>
          <div>
            <span className="text-zinc-500 uppercase tracking-wider font-mono">Day-1 Open</span>
            <p className="text-base font-bold text-lime-600 mt-0.5">2–3 Questions / Firm</p>
          </div>
        </div>
      </div>

      {/* Main Mode Tabs */}
      <div className="flex items-center gap-3 border-b border-zinc-200 pb-2">
        <button
          onClick={() => setActiveMainTab('packs')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeMainTab === 'packs'
              ? 'bg-zinc-900 text-white shadow-xs'
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
          }`}
        >
          <Building2 className="w-4 h-4" />
          50+ Company Placement Packs ({tracks.length})
        </button>

        <button
          onClick={() => setActiveMainTab('simulations')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeMainTab === 'simulations'
              ? 'bg-zinc-900 text-white shadow-xs'
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
          }`}
        >
          <Play className="w-4 h-4 text-lime-400" />
          Hiring Simulations
          <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-lime-500 text-zinc-950 font-bold">
            NEW
          </span>
        </button>

        <button
          onClick={() => setActiveMainTab('comprehension')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeMainTab === 'comprehension'
              ? 'bg-zinc-900 text-white shadow-xs'
              : 'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100'
          }`}
        >
          <Code2 className="w-4 h-4 text-indigo-500" />
          Code Comprehension
        </button>
      </div>

      {/* TAB 1: 50+ COMPANY PACKS */}
      {activeMainTab === 'packs' && (
        <div className="space-y-6">
          {/* Tier Filter Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-1.5 p-1 bg-zinc-100 border border-zinc-200 rounded-xl text-xs font-medium">
              <button
                onClick={() => setSelectedTier('all')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  selectedTier === 'all'
                    ? 'bg-white text-zinc-900 shadow-2xs font-semibold'
                    : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                All Tracks ({tracks.length})
              </button>
              <button
                onClick={() => setSelectedTier('gold')}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  selectedTier === 'gold'
                    ? 'bg-amber-50 text-amber-900 border border-amber-200 font-semibold'
                    : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Flame className="w-3.5 h-3.5 text-amber-600" />
                Gold Mine ({goldTracks.length})
              </button>
              <button
                onClick={() => setSelectedTier('silver')}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  selectedTier === 'silver'
                    ? 'bg-zinc-200 text-zinc-900 font-semibold'
                    : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Zap className="w-3.5 h-3.5 text-zinc-600" />
                Silver Mine ({silverTracks.length})
              </button>
              <button
                onClick={() => setSelectedTier('bronze')}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
                  selectedTier === 'bronze'
                    ? 'bg-orange-50 text-orange-900 border border-orange-200 font-semibold'
                    : 'text-zinc-600 hover:text-zinc-900'
                }`}
              >
                <Award className="w-3.5 h-3.5 text-amber-700" />
                Bronze Mine ({bronzeTracks.length})
              </button>
            </div>

            <div className="text-xs text-zinc-500 flex items-center gap-2 font-mono">
              <Unlock className="w-3.5 h-3.5 text-lime-600" />
              <span>Solve questions to unlock subsequent problems</span>
            </div>
          </div>

          {/* Grid of Company Cards */}
          {loading ? (
            <div className="py-20 text-center space-y-3">
              <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-zinc-500 font-mono">Loading community company packs...</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTracks.map((track) => {
                const Icon = ICON_MAP[track.logo_icon] || Building2;
                const unlockPct = Math.round((track.unlocked_count / Math.max(1, track.total_problems)) * 100);

                const tierStyle =
                  track.tier === 'gold'
                    ? 'border-amber-200 bg-gradient-to-br from-amber-50/20 to-white'
                    : track.tier === 'silver'
                    ? 'border-zinc-200 bg-white'
                    : 'border-orange-200 bg-gradient-to-br from-orange-50/20 to-white';

                return (
                  <Card
                    key={track.id}
                    className={`flex flex-col justify-between hover:shadow-md transition-all duration-200 border rounded-2xl ${tierStyle}`}
                  >
                    <div className="p-6 space-y-4">
                      {/* Card Header */}
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900">
                            <Icon className="w-5 h-5 text-zinc-900" />
                          </div>
                          <div>
                            <h3 className="font-bold text-base text-zinc-950 flex items-center gap-2">
                              {track.name}
                            </h3>
                            <p className="text-xs text-zinc-500">{track.role_title}</p>
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
                      <p className="text-xs text-zinc-600 line-clamp-2 leading-relaxed">
                        {track.description}
                      </p>

                      {/* Community Insight Callout */}
                      {track.community_tips && track.community_tips.length > 0 && (
                        <div className="bg-zinc-50 rounded-xl p-3 border border-zinc-200/80 text-[11px] space-y-1">
                          <span className="font-semibold text-zinc-800 flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
                            <Sparkles className="w-3 h-3 text-lime-600" />
                            Community Debrief Tip
                          </span>
                          <p className="text-zinc-600 italic line-clamp-2">
                            &ldquo;{track.community_tips[0]}&rdquo;
                          </p>
                        </div>
                      )}

                      {/* Unlock Progress Bar */}
                      <div className="space-y-1.5 pt-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="text-zinc-600 flex items-center gap-1">
                            <Unlock className="w-3 h-3 text-lime-600" />
                            {track.unlocked_count} of {track.total_problems} Unlocked
                          </span>
                          <span className="font-mono text-zinc-500">{unlockPct}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-100 rounded-full overflow-hidden border border-zinc-200">
                          <div
                            className="h-full bg-lime-500 rounded-full transition-all duration-300"
                            style={{ width: `${unlockPct}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Card Action Footer */}
                    <div className="px-6 py-3.5 bg-zinc-50/60 border-t border-zinc-100 flex items-center justify-between rounded-b-2xl">
                      <span className="text-[11px] text-zinc-500 font-mono">
                        3 Open Day-1
                      </span>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/tracks/${track.slug}`)}
                        className="gap-1.5 text-xs group bg-white border-zinc-200 hover:border-zinc-300"
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
      )}

      {/* TAB 2: PLACEMENT SIMULATIONS (Google, Uber, OpenAI) */}
      {activeMainTab === 'simulations' && (
        <div className="space-y-6">
          <div className="p-4 rounded-2xl bg-indigo-50/60 border border-indigo-200/80 text-xs text-indigo-900 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0" />
              <span>
                Timed and graded like the real thing: hidden tests, a real repository, unfamiliar code to read, and an interviewer who asks about the code you wrote. Unfinished attempts resume where you left off.
              </span>
            </div>
          </div>

          {simError && <p className="text-xs text-rose-600">{simError}</p>}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {simulations.map((sim) => {
              const Icon = ICON_MAP[sim.logo_icon] || Building2;

              return (
                <Card
                  key={sim.id}
                  className="flex flex-col justify-between border border-zinc-200 rounded-2xl bg-white shadow-xs hover:shadow-md transition-all"
                >
                  <div className="p-6 space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-11 h-11 rounded-2xl bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-900 shadow-2xs">
                          <Icon className="w-6 h-6" />
                        </div>
                        <div>
                          <h2 className="font-bold text-base text-zinc-950">{sim.company}</h2>
                          <p className="text-xs text-zinc-500">{sim.title}</p>
                        </div>
                      </div>
                      <Badge variant="warning" className="font-mono text-[10px] uppercase">
                        {sim.tier}
                      </Badge>
                    </div>

                    <p className="text-xs text-zinc-600 leading-relaxed font-medium">
                      {sim.tagline}
                    </p>

                    <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
                      <Clock className="w-3.5 h-3.5 text-zinc-400" />
                      <span>{sim.duration_minutes} minutes · {sim.rounds.length} rounds</span>
                    </div>

                    {/* Rounds Sequence */}
                    <div className="space-y-2 pt-2 border-t border-zinc-100">
                      <p className="text-[10px] uppercase font-mono font-bold text-zinc-400">
                        Exam Progression
                      </p>
                      {sim.rounds.map((round) => (
                        <div
                          key={round.round_number}
                          className="p-2.5 rounded-xl bg-zinc-50 border border-zinc-200/80 text-xs space-y-0.5"
                        >
                          <div className="flex items-center justify-between font-semibold text-zinc-900">
                            <span className="truncate">{round.name}</span>
                            <span className="text-[10px] font-mono text-zinc-400 shrink-0 ml-1">
                              {round.time_limit}m
                            </span>
                          </div>
                          <p className="text-[11px] font-mono text-zinc-700">{round.problem}</p>
                          <p className="text-[11px] text-zinc-500 line-clamp-2">{round.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="p-6 pt-0">
                    <Button
                      variant="primary"
                      className="w-full justify-center bg-zinc-900 hover:bg-zinc-800 text-white gap-2 text-xs"
                      onClick={() => startSimulation(sim.id)}
                      disabled={!!startingSim}
                    >
                      <Play className="w-3.5 h-3.5 text-lime-400" />
                      <span>{startingSim === sim.id ? 'Starting...' : `Start ${sim.company} simulation`}</span>
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: CODE COMPREHENSION (real, graded round) */}
      {activeMainTab === 'comprehension' && (
        <Card className="p-8 border-zinc-200 rounded-2xl bg-white shadow-xs max-w-3xl mx-auto space-y-5">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs text-zinc-500 font-mono">Code comprehension</span>
              <h2 className="text-xl font-bold text-zinc-900">Read code you didn't write. Find what breaks.</h2>
              <p className="text-sm text-zinc-600 leading-relaxed">
                Strong interviewers increasingly test reading over writing: explain unfamiliar production code, trace its
                output without running it, and point at the exact line that fails in production. Nine timed codebases,
                graded against verified answer keys, with a reviewer follow-up when you're close.
              </p>
            </div>
            <Code2 className="w-8 h-8 text-lime-600 shrink-0" />
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] font-mono text-zinc-600">
            {['caching', 'rate limiting', 'concurrency', 'retries', 'pagination', 'consistent hashing', 'async'].map((t) => (
              <span key={t} className="px-2 py-0.5 rounded bg-zinc-100 border border-zinc-200">{t}</span>
            ))}
          </div>
          <div className="flex justify-end">
            <Button onClick={() => navigate('/comprehension')} className="gap-2 text-xs">
              Start a comprehension round <Play className="w-3.5 h-3.5 text-lime-400" />
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};
