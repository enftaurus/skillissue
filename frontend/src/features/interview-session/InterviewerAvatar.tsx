import React, { useEffect, useRef } from 'react';
import { Volume2, VolumeX } from 'lucide-react';

interface InterviewerAvatarProps {
  isSpeaking: boolean;
  isListening: boolean;
  isThinking: boolean;
  autoSpeak: boolean;
  onToggleAutoSpeak: () => void;
  interviewerTitle?: string;
  category?: string;
}

export const InterviewerAvatar: React.FC<InterviewerAvatarProps> = ({
  isSpeaking,
  isListening,
  isThinking,
  autoSpeak,
  onToggleAutoSpeak,
  interviewerTitle = 'Senior Staff Engineer',
  category = 'technical',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let time = 0;

    const render = () => {
      time += 0.03;
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      // Determine state dynamic radius & color
      let baseRadius = 38;
      let primaryColor = '79, 70, 229'; // indigo-600
      let secondaryColor = '99, 102, 241'; // indigo-500

      if (isSpeaking) {
        // Dynamic pulse when interviewer speaks: Electric Indigo & Emerald
        baseRadius = 42 + Math.sin(time * 6) * 5 + Math.cos(time * 3) * 3;
        primaryColor = '79, 70, 229';
        secondaryColor = '16, 185, 129';
      } else if (isListening) {
        // Active candidate listening ripple: Vibrant Blue & Indigo
        baseRadius = 40 + Math.sin(time * 4) * 4;
        primaryColor = '59, 130, 246';
        secondaryColor = '99, 102, 241';
      } else if (isThinking) {
        // Rotating thinking mode: Amber & Orange
        baseRadius = 38 + Math.sin(time * 2) * 2;
        primaryColor = '245, 158, 11';
        secondaryColor = '217, 119, 6';
      } else {
        // Idle gentle breathing: Electric Indigo & Slate
        baseRadius = 38 + Math.sin(time * 1.5) * 1.5;
        primaryColor = '79, 70, 229';
        secondaryColor = '99, 102, 241';
      }

      // 1. Draw outer ambient glow
      const glowGrad = ctx.createRadialGradient(
        centerX,
        centerY,
        baseRadius * 0.5,
        centerX,
        centerY,
        baseRadius * 1.8
      );
      glowGrad.addColorStop(0, `rgba(${primaryColor}, 0.25)`);
      glowGrad.addColorStop(0.7, `rgba(${primaryColor}, 0.08)`);
      glowGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius * 1.8, 0, Math.PI * 2);
      ctx.fill();

      // 2. Draw audio-reactive wave rings
      const numRings = isSpeaking || isListening ? 3 : 2;
      for (let r = 1; r <= numRings; r++) {
        ctx.beginPath();
        const ringRad = baseRadius + r * 10 + (isSpeaking ? Math.sin(time * 4 + r) * 4 : 0);
        ctx.arc(centerX, centerY, ringRad, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${primaryColor}, ${0.35 / r})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 6]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 3. Draw central 3D shaded sphere with gradient
      const sphereGrad = ctx.createRadialGradient(
        centerX - baseRadius * 0.35,
        centerY - baseRadius * 0.35,
        baseRadius * 0.1,
        centerX,
        centerY,
        baseRadius
      );
      sphereGrad.addColorStop(0, '#FFFFFF');
      sphereGrad.addColorStop(0.3, `rgba(${primaryColor}, 0.85)`);
      sphereGrad.addColorStop(0.85, `rgba(${secondaryColor}, 0.95)`);
      sphereGrad.addColorStop(1, '#0F172A');

      ctx.fillStyle = sphereGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius, 0, Math.PI * 2);
      ctx.fill();

      // 4. Rotating orbital nodes
      const nodeCount = 5;
      for (let i = 0; i < nodeCount; i++) {
        const angle = time * 1.2 + (i * Math.PI * 2) / nodeCount;
        const orbitX = centerX + Math.cos(angle) * (baseRadius + 14);
        const orbitY = centerY + Math.sin(angle) * (baseRadius + 14) * 0.6; // perspective tilt

        ctx.fillStyle = `rgba(${primaryColor}, 0.9)`;
        ctx.beginPath();
        ctx.arc(orbitX, orbitY, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [isSpeaking, isListening, isThinking]);

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-xs flex flex-col items-center relative overflow-hidden">
      {/* Background radial accent */}
      <div className="absolute inset-0 bg-radial from-indigo-500/5 via-transparent to-transparent pointer-events-none" />

      {/* Top status bar */}
      <div className="w-full flex items-center justify-between text-xs mb-1">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isSpeaking
                ? 'bg-emerald-500 animate-ping'
                : isListening
                ? 'bg-blue-500 animate-ping'
                : isThinking
                ? 'bg-amber-500 animate-spin'
                : 'bg-indigo-500'
            }`}
          />
          <span className="font-semibold text-slate-700 text-xs uppercase tracking-wider">
            {isSpeaking
              ? 'Speaking Question'
              : isListening
              ? 'Listening To You'
              : isThinking
              ? 'Evaluating...'
              : 'Interviewer Presence'}
          </span>
        </div>

        <button
          onClick={onToggleAutoSpeak}
          title={autoSpeak ? 'Disable AI Voice' : 'Enable AI Voice'}
          className="p-1.5 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-slate-100 transition-colors"
        >
          {autoSpeak ? (
            <Volume2 className="w-4 h-4 text-indigo-600" />
          ) : (
            <VolumeX className="w-4 h-4 text-slate-400" />
          )}
        </button>
      </div>

      {/* 3D Audio-Reactive Sphere Canvas */}
      <div className="relative my-2 flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={180}
          height={130}
          className="w-[180px] h-[130px]"
        />
      </div>

      {/* Avatar Identity & Role */}
      <div className="text-center space-y-1">
        <div className="font-bold text-sm text-slate-900">{interviewerTitle}</div>
        <div className="text-xs text-slate-500 font-mono uppercase tracking-wider">
          Persona: Gilfoyle Rigor · {category}
        </div>
      </div>

      {/* Audio Wave Bars visualizer */}
      <div className="flex items-center gap-1 mt-3 h-3.5">
        {[0.4, 0.8, 1.0, 0.6, 0.9, 0.5, 0.7].map((heightScale, i) => (
          <span
            key={i}
            className={`w-1 rounded-full transition-all duration-150 ${
              isSpeaking
                ? 'bg-emerald-500'
                : isListening
                ? 'bg-blue-500'
                : 'bg-slate-200'
            }`}
            style={{
              height:
                isSpeaking || isListening
                  ? `${Math.max(4, heightScale * 14)}px`
                  : '4px',
            }}
          />
        ))}
      </div>
    </div>
  );
};
