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

const colorMap: Record<Color, { bg: string; text: string; border: string }> = {
  blue:   { bg: 'rgba(88,166,255,0.15)',  text: '#58A6FF', border: 'rgba(88,166,255,0.3)' },
  green:  { bg: 'rgba(63,185,80,0.15)',   text: '#3FB950', border: 'rgba(63,185,80,0.3)' },
  orange: { bg: 'rgba(210,153,34,0.15)',  text: '#D29922', border: 'rgba(210,153,34,0.3)' },
  red:    { bg: 'rgba(248,81,73,0.15)',   text: '#F85149', border: 'rgba(248,81,73,0.3)' },
  purple: { bg: 'rgba(163,113,247,0.15)', text: '#A371F7', border: 'rgba(163,113,247,0.3)' },
  cyan:   { bg: 'rgba(86,212,221,0.15)',  text: '#56D4DD', border: 'rgba(86,212,221,0.3)' },
  gray:   { bg: 'rgba(110,118,129,0.15)', text: '#8B949E', border: 'rgba(110,118,129,0.3)' },
};

export function Badge({ color = 'gray', size = 'sm', children, className = '' }: BadgeProps) {
  const c = colorMap[color];
  const padding = size === 'sm' ? '2px 8px' : '4px 10px';
  const fontSize = size === 'sm' ? '11px' : '12px';
  return (
    <span
      className={['inline-flex items-center font-medium rounded-full', className].join(' ')}
      style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        padding,
        fontSize,
        lineHeight: '1.4',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
