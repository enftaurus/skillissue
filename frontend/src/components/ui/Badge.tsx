import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'lime' | 'zinc' | 'amber' | 'red' | 'blue' | 'emerald' | 'rose';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'zinc',
  size = 'md',
  className = '',
}) => {
  const variants = {
    lime: 'bg-lime-100 text-lime-900 border-lime-200',
    zinc: 'bg-zinc-100 text-zinc-800 border-zinc-200',
    amber: 'bg-amber-100 text-amber-900 border-amber-200',
    red: 'bg-red-100 text-red-900 border-red-200',
    rose: 'bg-rose-100 text-rose-900 border-rose-200',
    emerald: 'bg-emerald-100 text-emerald-900 border-emerald-200',
    blue: 'bg-blue-100 text-blue-900 border-blue-200',
  };

  const sizes = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  );
};
