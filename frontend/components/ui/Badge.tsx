'use client';
import type { ReactNode } from 'react';

type Color = 'blue' | 'green' | 'orange' | 'red' | 'purple' | 'cyan' | 'gray';
type Size = 'sm' | 'md';

interface BadgeProps {
  color?: Color;
  size?: Size;
  children: ReactNode;
  className?: string;
}

// Map legacy color names onto the tightened token palette.
const colorMap: Record<Color, { bg: string; text: string; border: string }> = {
  blue:   { bg: 'var(--accent-subtle)',  text: 'var(--accent)',         border: 'var(--border-accent)' },
  green:  { bg: 'var(--success-subtle)', text: 'var(--success)',        border: 'color-mix(in srgb, var(--success) 30%, transparent)' },
  orange: { bg: 'var(--warning-subtle)', text: 'var(--warning)',        border: 'color-mix(in srgb, var(--warning) 30%, transparent)' },
  red:    { bg: 'var(--danger-subtle)',  text: 'var(--danger)',         border: 'color-mix(in srgb, var(--danger) 30%, transparent)' },
  purple: { bg: 'var(--accent-subtle)',  text: 'var(--accent)',         border: 'var(--border-accent)' },
  cyan:   { bg: 'var(--accent-subtle)',  text: 'var(--accent)',         border: 'var(--border-accent)' },
  gray:   { bg: 'color-mix(in srgb, var(--text-muted) 15%, transparent)', text: 'var(--text-secondary)', border: 'var(--border-default)' },
};

export function Badge({ color = 'gray', size = 'sm', children, className = '' }: BadgeProps) {
  const c = colorMap[color];
  const padding = size === 'sm' ? '2px 8px' : '3px 10px';
  return (
    <span
      className={['inline-flex items-center font-medium rounded-full', className].join(' ')}
      style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        padding,
        fontSize: 'var(--text-xs)',
        lineHeight: 1.5,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
