'use client';
import { useId } from 'react';
import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = '', id, ...rest }: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const errorId = `${inputId}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-[13px] font-medium text-[var(--text-secondary)]">
          {label}
        </label>
      )}
      <input
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        className={[
          'app-input w-full rounded-[var(--radius-sm)] bg-[var(--bg-elevated)] px-3 py-2 text-[14px] text-[var(--text-primary)]',
          error ? 'app-input--error' : '',
          className,
        ].join(' ')}
        {...rest}
      />
      {error && (
        <span id={errorId} className="text-[12px] text-[var(--danger)]">{error}</span>
      )}
      <style jsx>{`
        .app-input {
          border: 1px solid var(--border-default);
          outline: none;
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        .app-input::placeholder { color: var(--text-muted); }
        .app-input:hover { border-color: var(--border-strong); }
        .app-input:focus {
          border-color: var(--accent);
          box-shadow: 0 0 0 3px var(--accent-subtle);
        }
        .app-input--error { border-color: var(--danger); }
        .app-input--error:focus {
          box-shadow: 0 0 0 3px var(--danger-subtle);
        }
      `}</style>
    </div>
  );
}

export default Input;
