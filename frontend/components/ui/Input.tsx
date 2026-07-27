'use client';
import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = '', style, ...rest }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}
        >
          {label}
        </label>
      )}
      <input
        className={className}
        style={{
          background: 'var(--bg-elevated)',
          border: `1px solid ${error ? 'var(--accent-red)' : 'var(--border-default)'}`,
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-primary)',
          padding: '8px 12px',
          fontSize: '14px',
          outline: 'none',
          width: '100%',
          transition: 'border-color 0.15s',
          ...style,
        }}
        onFocus={(e) => {
          (e.target as HTMLInputElement).style.borderColor = 'var(--accent-blue)';
        }}
        onBlur={(e) => {
          (e.target as HTMLInputElement).style.borderColor = error
            ? 'var(--accent-red)'
            : 'var(--border-default)';
        }}
        {...rest}
      />
      {error && (
        <span style={{ fontSize: '12px', color: 'var(--accent-red)' }}>{error}</span>
      )}
    </div>
  );
}

export default Input;
