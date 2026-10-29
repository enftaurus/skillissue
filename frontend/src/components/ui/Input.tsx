import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  showPasswordToggle?: boolean;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  id,
  type = 'text',
  showPasswordToggle = false,
  ...props
}) => {
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const isPassword = type === 'password';
  const effectiveType = isPassword && showPasswordToggle ? (isPasswordVisible ? 'text' : 'password') : type;

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-semibold text-ink-muted uppercase tracking-wider">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type={effectiveType}
          className={`w-full px-3 py-2 text-sm bg-white border rounded-md text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 transition-colors disabled:bg-surface-subtle disabled:cursor-not-allowed ${
            isPassword && showPasswordToggle ? 'pr-10' : ''
          } ${
            error ? 'border-red-500 focus:ring-red-500' : 'border-surface-border'
          } ${className}`}
          {...props}
        />
        {isPassword && showPasswordToggle && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setIsPasswordVisible((prev) => !prev)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink focus:outline-none p-1 rounded transition-colors"
            title={isPasswordVisible ? 'Hide password' : 'Show password'}
            aria-label={isPasswordVisible ? 'Hide password' : 'Show password'}
          >
            {isPasswordVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {error && <p className="text-xs text-red-600 mt-1 font-medium">{error}</p>}
      {helperText && !error && <p className="text-xs text-ink-subtle mt-1">{helperText}</p>}
    </div>
  );
};
