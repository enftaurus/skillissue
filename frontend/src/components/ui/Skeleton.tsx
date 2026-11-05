import React from 'react';

/** Shimmering placeholder block; respects prefers-reduced-motion via the global rule. */
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div
    aria-hidden
    className={`rounded-xl bg-[linear-gradient(90deg,#f1f5f9_25%,#e2e8f0_50%,#f1f5f9_75%)] bg-[length:200%_100%] animate-shimmer ${className}`}
  />
);

/** Page-shaped loading states, so layout doesn't jump when data arrives. */
export const PageSkeleton: React.FC<{ variant?: 'dashboard' | 'report' | 'workspace'; label?: string }> = ({
  variant = 'dashboard',
  label = 'Loading',
}) => (
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6" role="status" aria-label={label}>
    <span className="sr-only">{label}…</span>
    {variant === 'dashboard' && (
      <>
        <Skeleton className="h-44" />
        <div className="grid md:grid-cols-3 gap-6">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
        <div className="grid lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </>
    )}
    {variant === 'report' && (
      <>
        <Skeleton className="h-10 w-2/3" />
        <div className="grid lg:grid-cols-3 gap-6">
          <Skeleton className="h-56" />
          <Skeleton className="h-56 lg:col-span-2" />
        </div>
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </>
    )}
    {variant === 'workspace' && (
      <>
        <Skeleton className="h-16" />
        <div className="grid lg:grid-cols-[1fr_2fr] gap-6">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </>
    )}
  </div>
);
