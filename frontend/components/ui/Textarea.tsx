'use client';

import { useId } from 'react';
import type { TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function Textarea({ label, error, className = '', id, ...rest }: TextareaProps) {
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
      <textarea
        id={inputId}
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        className={[
          'input-field app-textarea',
          error ? 'app-textarea--error' : '',
          className,
        ].join(' ')}
        {...rest}
      />
      {error && (
        <span id={errorId} className="text-[12px] text-[var(--danger)]">{error}</span>
      )}
    </div>
  );
}

export default Textarea;
