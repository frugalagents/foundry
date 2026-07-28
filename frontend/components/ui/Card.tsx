'use client';
import type { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Emphasize with an accent border instead of the amateur glow. */
  glow?: boolean;
  /** Lift + border-accent on hover (for clickable cards). */
  hover?: boolean;
}

export function Card({ children, glow, hover, className = '', style, ...rest }: CardProps) {
  return (
    <div
      className={[
        'card-base rounded-[var(--radius-md)]',
        hover ? 'card-hover' : '',
        glow ? 'card-emphasis' : '',
        className,
      ].join(' ')}
      style={style}
      {...rest}
    >
      {children}
      <style jsx>{`
        .card-base {
          background: var(--bg-card);
          border: 1px solid var(--border-default);
          box-shadow: var(--shadow-card);
          transition: background 0.15s, border-color 0.15s, box-shadow 0.15s, transform 0.15s;
        }
        .card-hover {
          cursor: pointer;
        }
        .card-hover:hover {
          background: var(--bg-elevated);
          border-color: var(--border-strong);
          transform: translateY(-1px);
        }
        .card-emphasis {
          border-color: var(--border-accent);
        }
      `}</style>
    </div>
  );
}

export default Card;
