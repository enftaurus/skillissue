import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'lime' | 'brand' | 'indigo' | 'zinc' | 'amber' | 'red' | 'blue' | 'emerald' | 'rose';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'zinc',
  size = 'md',
  className = '',
}) => {
  const variants = {
    brand: 'bg-indigo-50 text-indigo-700 border-indigo-200/70',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200/70',
    lime: 'bg-indigo-50 text-indigo-700 border-indigo-200/70', // Seamlessly upgrades legacy lime references to Indigo
    zinc: 'bg-slate-100 text-slate-700 border-slate-200',
    amber: 'bg-amber-50 text-amber-800 border-amber-200/80',
    red: 'bg-rose-50 text-rose-700 border-rose-200/80',
    rose: 'bg-rose-50 text-rose-700 border-rose-200/80',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/70',
    blue: 'bg-sky-50 text-sky-700 border-sky-200/80',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-0.5',
    md: 'text-xs px-3 py-1 font-medium',
    lg: 'text-sm px-3.5 py-1.5 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border shadow-2xs ${variants[variant] || variants.zinc} ${sizes[size]} ${className}`}
    >
      {children}
    </span>
  );
};
