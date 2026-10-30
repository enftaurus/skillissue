import React from 'react';

interface AudioWaveformProps {
  isActive: boolean;
  label?: string;
  className?: string;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({ isActive, label, className = '' }) => {
  return (
    <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-subtle border border-surface-border text-xs ${className}`}>
      <div className="flex items-center gap-0.5 h-4">
        {[40, 80, 60, 100, 50].map((heightPct, idx) => (
          <span
            key={idx}
            className={`w-0.5 rounded-full transition-all duration-150 ${
              isActive
                ? 'bg-emerald-500 animate-pulse'
                : 'bg-zinc-300'
            }`}
            style={{
              height: isActive ? `${Math.max(20, (heightPct * ((idx % 2 === 0 ? 1 : 0.7))))}%` : '20%',
              animationDelay: `${idx * 120}ms`,
            }}
          />
        ))}
      </div>
      {label && (
        <span className={`text-xs font-medium ${isActive ? 'text-emerald-700 font-semibold' : 'text-ink-muted'}`}>
          {label}
        </span>
      )}
    </div>
  );
};
