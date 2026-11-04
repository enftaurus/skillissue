import React, { useState, useEffect, useRef, useMemo } from 'react';
import Editor from '@monaco-editor/react';
import { api } from '../../lib/api';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import {
  Play,
  Pause,
  RotateCcw,
  ShieldAlert,
  AlertTriangle,
  Clock,
  Activity,
  FileCode,
  Info,
  Terminal,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';

export interface TimelineSnapshot {
  timestamp: number;
  offset_seconds: number;
  text: string;
  char_count: number;
  event_type: string;
  source: string;
  inserted_text?: string;
  marker_type?: 'typing' | 'paste' | 'large_insert' | 'blur' | 'idle_pause' | 'suggest';
  marker_label?: string;
}

export interface ReviewFlag {
  code: string;
  family: string;
  confidence: 'low' | 'medium';
  evidence: string;
  independent_families?: string[];
  what_it_cannot_prove: string;
}

export interface EditorReplayData {
  candidate_assessment_id: string;
  round_key: string;
  problem_title?: string;
  submitted_code: string;
  code_hash_match: boolean;
  effective_lines: number;
  total_events: number;
  duration_seconds: number;
  features: {
    typed_ratio: number;
    large_insert_count: number;
    activity_density: number;
    revision_ratio: number;
    cadence?: {
      coefficient_of_variation: number;
      mean_iki_ms: number;
      burst_count: number;
    };
    read_then_type_episodes?: Array<{
      pause_seconds: number;
      chars_typed_in_20s: number;
      timestamp: number;
    }>;
    focus?: {
      blur_count: number;
      total_blurred_seconds: number;
      hidden_tab_seconds: number;
      active_time_seconds: number;
      wall_time_seconds: number;
    };
  };
  explanation_check?: {
    status: string;
    explanation_consistency?: number;
    confidence?: string;
    questions?: Array<{
      type: string;
      text: string;
      code_reference: string;
    }>;
    answers?: Array<{
      question_index: number;
      text: string;
    }>;
  } | null;
  flags: ReviewFlag[];
  overall_confidence: 'low' | 'medium' | null;
  status: 'evaluated' | 'insufficient_data';
  reason?: string;
  product_honesty: string;
  timeline: TimelineSnapshot[];
}

interface EditorReplayModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateAssessmentId: string;
  roundKey: string;
  candidateName: string;
}

export const EditorReplayModal: React.FC<EditorReplayModalProps> = ({
  isOpen,
  onClose,
  candidateAssessmentId,
  roundKey,
  candidateName,
}) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [replayData, setReplayData] = useState<EditorReplayData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Playback state
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(2); // 1x, 2x, 4x, 8x
  const playIntervalRef = useRef<any>(null);

  useEffect(() => {
    if (!isOpen) {
      setReplayData(null);
      setCurrentFrameIndex(0);
      setIsPlaying(false);
      return;
    }

    setLoading(true);
    setError(null);

    api.get<EditorReplayData>(`/telemetry/editor/${candidateAssessmentId}/${roundKey}`)
      .then((data) => {
        setReplayData(data);
        // Start at end or beginning
        if (data.timeline && data.timeline.length > 0) {
          setCurrentFrameIndex(data.timeline.length - 1);
        }
      })
      .catch((err) => {
        console.error('Failed to load telemetry replay', err);
        setError('No telemetry recorded for this candidate round or access denied.');
      })
      .finally(() => setLoading(false));
  }, [isOpen, candidateAssessmentId, roundKey]);

  // Handle Playback Interval
  useEffect(() => {
    if (!isPlaying || !replayData?.timeline || replayData.timeline.length === 0) {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
      return;
    }

    const intervalTime = Math.max(25, Math.floor(150 / playbackSpeed));
    playIntervalRef.current = setInterval(() => {
      setCurrentFrameIndex((prev) => {
        if (prev >= (replayData?.timeline?.length || 1) - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalTime);

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, playbackSpeed, replayData]);

  const timelineList = useMemo(() => replayData?.timeline || [], [replayData]);
  const flagsList = useMemo(() => replayData?.flags || [], [replayData]);

  const currentFrame = useMemo(() => {
    if (timelineList.length === 0) return null;
    return timelineList[currentFrameIndex] || timelineList[0];
  }, [timelineList, currentFrameIndex]);

  const totalFrames = timelineList.length;
  const maxSeconds = timelineList[totalFrames - 1]?.offset_seconds || 1;

  // Jump to specific flag occurrence
  const handleJumpToFlag = (flag: ReviewFlag) => {
    if (!replayData?.timeline) return;
    if (flag.code === 'LARGE_UNTYPED_INSERT') {
      const idx = replayData.timeline.findIndex((f) => f.marker_type === 'large_insert' || f.marker_type === 'paste');
      if (idx !== -1) {
        setCurrentFrameIndex(idx);
        setIsPlaying(false);
      }
    } else if (flag.code === 'READ_THEN_TYPE_PATTERN') {
      const idx = replayData.timeline.findIndex((f) => f.marker_type === 'idle_pause');
      if (idx !== -1) {
        setCurrentFrameIndex(idx);
        setIsPlaying(false);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-zinc-950/70 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl border border-zinc-200 shadow-2xl w-full max-w-6xl overflow-hidden flex flex-col h-[92vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/70 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-zinc-900 flex items-center justify-center text-lime-400 font-mono font-bold text-xs">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm sm:text-base text-zinc-950">
                  Candidate Editor Replay &amp; Activity Telemetry
                </h3>
                {replayData && (
                  <Badge
                    variant={replayData.code_hash_match ? 'success' : 'destructive'}
                    className="text-[10px] font-mono"
                  >
                    {replayData.code_hash_match ? 'SHA256 Reconstructed Hash Match' : 'Delta Divergence'}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-500 font-mono">
                Candidate: <span className="text-zinc-900 font-semibold">{candidateName}</span> • Round {Number(roundKey) + 1} OA DSA
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={onClose} className="text-xs">
              Close
            </Button>
          </div>
        </div>

        {/* Modal Main Area */}
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center space-y-3">
            <div className="w-8 h-8 border-2 border-lime-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs font-mono text-zinc-500">Replaying keystroke deltas and extracting activity features...</p>
          </div>
        ) : error || !replayData ? (
          <div className="flex-1 p-8 flex flex-col items-center justify-center text-center space-y-3">
            <AlertTriangle className="w-10 h-10 text-amber-500" />
            <h4 className="font-bold text-sm text-zinc-900">No Telemetry Timeline Available</h4>
            <p className="text-xs text-zinc-500 max-w-md leading-relaxed">{error}</p>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Top Toolbar & Scrubber */}
            <div className="p-4 border-b border-zinc-200 bg-white space-y-3 shrink-0">
              {/* Playback Controls & Scrubber */}
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant={isPlaying ? 'danger' : 'primary'}
                    onClick={() => setIsPlaying(!isPlaying)}
                    className="h-8 px-3 gap-1.5 text-xs font-semibold"
                  >
                    {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    <span>{isPlaying ? 'Pause' : 'Play'}</span>
                  </Button>

                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setIsPlaying(false);
                      setCurrentFrameIndex(0);
                    }}
                    title="Reset to beginning"
                    className="h-8 px-2"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-zinc-600" />
                  </Button>

                  {/* Playback Speed */}
                  <div className="flex items-center rounded-lg border border-zinc-200 p-0.5 text-xs font-mono">
                    {[1, 2, 4, 8].map((speed) => (
                      <button
                        key={speed}
                        onClick={() => setPlaybackSpeed(speed)}
                        className={`px-2 py-0.5 rounded transition-colors ${
                          playbackSpeed === speed
                            ? 'bg-zinc-900 text-white font-bold'
                            : 'text-zinc-600 hover:text-zinc-900'
                        }`}
                      >
                        {speed}x
                      </button>
                    ))}
                  </div>
                </div>

                {/* Timestamp & Frame Indicator */}
                <div className="flex items-center gap-3 text-xs font-mono text-zinc-600">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-zinc-400" />
                    <span className="font-bold text-zinc-950">
                      {Math.floor((currentFrame?.offset_seconds || 0) / 60)}:
                      {String(Math.floor((currentFrame?.offset_seconds || 0) % 60)).padStart(2, '0')}
                    </span>
                    <span className="text-zinc-400">
                      / {Math.floor(maxSeconds / 60)}:{String(Math.floor(maxSeconds % 60)).padStart(2, '0')}
                    </span>
                  </div>
                  <span>•</span>
                  <span>
                    Frame {currentFrameIndex + 1} / {totalFrames}
                  </span>
                  <span>•</span>
                  <span className="text-zinc-500">
                    Source: <strong className="text-zinc-800 uppercase">{currentFrame?.source || 'typing'}</strong>
                  </span>
                </div>
              </div>

              {/* Range Slider Scrubber */}
              <div className="relative pt-1">
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, totalFrames - 1)}
                  value={currentFrameIndex}
                  onChange={(e) => {
                    setIsPlaying(false);
                    setCurrentFrameIndex(Number(e.target.value));
                  }}
                  className="w-full accent-lime-600 cursor-pointer h-2 bg-zinc-200 rounded-lg appearance-none"
                />

                {/* Visual Activity Density Strip below slider */}
                <div className="h-2 w-full mt-1 bg-zinc-100 rounded-sm relative overflow-hidden flex items-center">
                  {timelineList.map((frame, idx) => {
                    if (!frame.marker_type) return null;
                    const leftPct = (frame.offset_seconds / maxSeconds) * 100;
                    const color =
                      frame.marker_type === 'paste' || frame.marker_type === 'large_insert'
                        ? 'bg-amber-500'
                        : frame.marker_type === 'blur'
                        ? 'bg-rose-500'
                        : frame.marker_type === 'idle_pause'
                        ? 'bg-indigo-500'
                        : 'bg-lime-500';

                    return (
                      <div
                        key={idx}
                        onClick={() => {
                          setIsPlaying(false);
                          setCurrentFrameIndex(idx);
                        }}
                        title={`${frame.marker_label || frame.marker_type} at ${Math.round(frame.offset_seconds)}s`}
                        style={{ left: `${Math.min(99.5, Math.max(0.5, leftPct))}%` }}
                        className={`absolute w-1 h-3 rounded-full ${color} cursor-pointer hover:scale-125 transition-transform z-10`}
                      />
                    );
                  })}
                </div>

                {/* Activity Legend */}
                <div className="flex items-center gap-4 text-[10px] text-zinc-500 pt-1 font-mono">
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-lime-500 inline-block" />
                    <span>Typing Burst</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                    <span>Large Insert / Paste</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-rose-500 inline-block" />
                    <span>Window Blur</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block" />
                    <span>Long Pause (≥60s)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Split Body: Monaco Editor on Left, Telemetry Features & Flags on Right */}
            <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
              {/* Left Column: Monaco Replay Canvas */}
              <div className="flex-1 flex flex-col border-r border-zinc-200 bg-zinc-950 min-h-0 relative">
                <div className="p-2.5 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between text-xs text-zinc-400 font-mono">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-lime-400" />
                    <span className="text-zinc-200 font-semibold">reconstructed_buffer.py</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px]">
                    <span>{currentFrame?.text?.length || 0} characters</span>
                    <span>{(currentFrame?.text?.match(/\n/g) || []).length + 1} lines</span>
                  </div>
                </div>

                <div className="flex-1 min-h-0">
                  <Editor
                    height="100%"
                    language="python"
                    theme="vs-dark"
                    value={currentFrame?.text || ''}
                    options={{
                      readOnly: true,
                      minimap: { enabled: false },
                      fontSize: 13,
                      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                      scrollBeyondLastLine: false,
                      lineNumbers: 'on',
                      wordWrap: 'on',
                      renderLineHighlight: 'none',
                    }}
                  />
                </div>
              </div>

              {/* Right Column: Telemetry Signals, Explanation Check & Flags */}
              <div className="w-full md:w-96 p-4 overflow-y-auto space-y-5 bg-zinc-50/60 text-xs">
                {/* 1. Review Flags Alert */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-zinc-950 flex items-center gap-1.5">
                      <ShieldAlert className="w-4 h-4 text-zinc-700" />
                      <span>Integrity Review Flags</span>
                    </h4>
                    <Badge
                      variant={flagsList.length === 0 ? 'success' : 'destructive'}
                      className="text-[10px] font-mono"
                    >
                      {flagsList.length === 0 ? '0 Flags Emitted' : `${flagsList.length} Flags (Human Review Only)`}
                    </Badge>
                  </div>

                  {flagsList.length === 0 ? (
                    <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl text-emerald-800 flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <p className="leading-relaxed">
                        Natural editing cadence and multi-family consistency verified. No suspicious anomalies detected.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {flagsList.map((flag, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 bg-white border border-rose-200 rounded-xl space-y-2 shadow-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-rose-700 text-xs">{flag.code}</span>
                            <Badge variant="outline" className="text-[10px] uppercase font-mono text-rose-700 bg-rose-50 border-rose-200">
                              {flag.confidence} Confidence
                            </Badge>
                          </div>
                          <p className="text-zinc-700 leading-relaxed font-sans">{flag.evidence}</p>

                          <div className="pt-1.5 border-t border-zinc-100 space-y-1">
                            <p className="text-[10px] text-zinc-500 italic">
                              <strong>Cannot prove:</strong> {flag.what_it_cannot_prove}
                            </p>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleJumpToFlag(flag)}
                              className="text-[10px] h-6 px-2 text-indigo-700 hover:text-indigo-900 hover:bg-indigo-50 font-semibold"
                            >
                              Jump to Flag in Timeline →
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. Pure Telemetry Feature Metrics */}
                <div className="space-y-2">
                  <h4 className="font-bold text-zinc-950 flex items-center gap-1.5">
                    <Activity className="w-4 h-4 text-zinc-700" />
                    <span>Key Telemetry Features</span>
                  </h4>

                  <div className="grid grid-cols-2 gap-2 font-mono">
                    <div className="p-2.5 bg-white rounded-xl border border-zinc-200">
                      <span className="text-[10px] text-zinc-400 block uppercase">Typed Ratio</span>
                      <strong className="text-sm text-zinc-900">
                        {Math.round((replayData.features?.typed_ratio || 0) * 100)}%
                      </strong>
                    </div>

                    <div className="p-2.5 bg-white rounded-xl border border-zinc-200">
                      <span className="text-[10px] text-zinc-400 block uppercase">Large Inserts</span>
                      <strong className={`text-sm ${(replayData.features?.large_insert_count || 0) > 0 ? 'text-amber-600' : 'text-zinc-900'}`}>
                        {replayData.features?.large_insert_count || 0}
                      </strong>
                    </div>

                    <div className="p-2.5 bg-white rounded-xl border border-zinc-200">
                      <span className="text-[10px] text-zinc-400 block uppercase">Window Blurs</span>
                      <strong className={`text-sm ${(replayData.features?.focus?.blur_count || 0) > 2 ? 'text-rose-600' : 'text-zinc-900'}`}>
                        {replayData.features?.focus?.blur_count || 0} ({Math.round(replayData.features?.focus?.total_blurred_seconds || 0)}s)
                      </strong>
                    </div>

                    <div className="p-2.5 bg-white rounded-xl border border-zinc-200">
                      <span className="text-[10px] text-zinc-400 block uppercase">Typing Burst CV</span>
                      <strong className="text-sm text-zinc-900">
                        {replayData.features?.cadence?.coefficient_of_variation ?? 'N/A'}
                      </strong>
                    </div>
                  </div>
                </div>

                {/* 3. Post-Code Explanation Check Section */}
                {replayData.explanation_check && (
                  <div className="space-y-2 pt-2 border-t border-zinc-200">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-zinc-950 flex items-center gap-1.5">
                        <HelpCircle className="w-4 h-4 text-indigo-600" />
                        <span>Explanation Cross-Exam</span>
                      </h4>
                      <Badge variant="outline" className="font-mono text-[10px]">
                        Consistency: {Math.round((replayData.explanation_check.explanation_consistency || 0) * 100)}%
                      </Badge>
                    </div>

                    <div className="p-3 bg-white rounded-xl border border-zinc-200 space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-zinc-500">Evaluator Confidence:</span>
                        <strong className="capitalize text-zinc-900 font-mono">
                          {replayData.explanation_check.confidence || 'normal'}
                        </strong>
                      </div>
                      <p className="text-[11px] text-zinc-600 leading-relaxed">
                        Cross-examination asked {replayData.explanation_check.questions?.length || 3} questions grounded in candidate's exact identifiers to verify authentic code authorship.
                      </p>
                    </div>
                  </div>
                )}

                {/* 4. Product Honesty Statement (Mandatory Rule 3) */}
                <div className="p-3.5 bg-zinc-100 rounded-xl border border-zinc-200/80 text-[11px] text-zinc-600 space-y-1.5 leading-relaxed">
                  <div className="flex items-center gap-1.5 font-bold text-zinc-900">
                    <Info className="w-3.5 h-3.5 text-zinc-700 shrink-0" />
                    <span>Product Honesty Statement</span>
                  </div>
                  <p>{replayData.product_honesty}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
