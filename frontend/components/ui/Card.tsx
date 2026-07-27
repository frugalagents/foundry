'use client';
import type { HTMLAttributes, ReactNode } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  glow?: boolean;
  hover?: boolean;
}

export function Card({ children, glow, hover, className = '', style, ...rest }: CardProps) {
  return (
    <div
      className={['rounded-[var(--radius-md)] transition-all duration-200', className].join(' ')}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        boxShadow: glow
          ? 'var(--glow-accent), var(--shadow-card)'
          : 'var(--shadow-card)',
        ...style,
      }}
      {...(hover
        ? {
            onMouseEnter: (e) => {
              (e.currentTarget as HTMLDivElement).style.background =
                'var(--bg-elevated)';
            },
            onMouseLeave: (e) => {
              (e.currentTarget as HTMLDivElement).style.background =
                'var(--bg-card)';
            },
          }
        : {})}
      {...rest}
    >
      {children}
    </div>
  );
}

export default Card;
