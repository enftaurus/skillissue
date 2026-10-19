import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`w-full px-3 py-2 text-sm bg-white border rounded-md text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 transition-colors disabled:bg-surface-subtle disabled:cursor-not-allowed ${
          error ? 'border-red-500 focus:ring-red-500' : 'border-surface-border'
        } ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-600 mt-1 font-medium">{error}</p>}
      {helperText && !error && <p className="text-xs text-ink-subtle mt-1">{helperText}</p>}
    </div>
  );
};
