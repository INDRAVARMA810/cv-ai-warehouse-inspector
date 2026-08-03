import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';
import { eventLevelTone, levelTone, statusTone } from '@/utils/severity';

interface BadgeProps {
  children: ReactNode;
  className?: string;
  /** Renders a small leading dot, useful for status pills. */
  dot?: boolean;
}

/** Neutral pill. Prefer the specific badges below where they apply. */
export function Badge({ children, className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium leading-5 tracking-wide',
        'border-surface-600 bg-surface-700/40 text-content-secondary',
        className,
      )}
    >
      {dot ? <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" /> : null}
      {children}
    </span>
  );
}

/** Alert urgency, coloured by the shared severity scale. */
export function LevelBadge({ level, className }: { level: string; className?: string }) {
  const tone = levelTone(level);
  return (
    <Badge dot className={cn(tone.text, tone.bg, tone.border, className)}>
      {tone.label}
    </Badge>
  );
}

/** Alert lifecycle status. */
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const tone = statusTone(status);
  return (
    <Badge dot className={cn(tone.text, tone.bg, tone.border, className)}>
      {tone.label}
    </Badge>
  );
}

/** System-event level, mapped onto the same visual scale. */
export function EventLevelBadge({ level, className }: { level: string; className?: string }) {
  const tone = eventLevelTone(level);
  return (
    <Badge dot className={cn(tone.text, tone.bg, tone.border, className)}>
      {level.toUpperCase()}
    </Badge>
  );
}
