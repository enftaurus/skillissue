import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`bg-white rounded-lg border border-surface-border shadow-card p-6 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
