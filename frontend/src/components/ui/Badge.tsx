import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';
import { eventLevelTone, levelTone, statusTone } from '@/utils/severity';

interface BadgeProps {
  children: ReactNode;
  className?: string;
  /** Leading LED. */
  dot?: boolean;
  /** Pulses the LED — reserve for genuinely live/urgent state. */
  live?: boolean;
}

/**
 * Status pill.
 *
 * Squared off with a tight radius and uppercase mono type: this is a
 * readout, not a tag. Prefer the specific badges below so severity
 * colour is never chosen at the call site.
 */
export function Badge({ children, className, dot, live }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-control border px-1.5 py-0.5',
        'font-mono text-2xs font-medium uppercase leading-4 tracking-wider',
        'border-edge bg-edge-soft text-ink-dim',
        className,
      )}
    >
      {dot ? (
        <span
          className={cn(
            'h-1.5 w-1.5 shrink-0 rounded-full bg-current',
            live && 'animate-led-pulse',
          )}
        />
      ) : null}
      {children}
    </span>
  );
}

/** Alert urgency. */
export function LevelBadge({
  level,
  className,
  live,
}: {
  level: string;
  className?: string;
  live?: boolean;
}) {
  const tone = levelTone(level);
  return (
    <Badge dot live={live} className={cn(tone.text, tone.bg, tone.border, className)}>
      {tone.label}
    </Badge>
  );
}

/** Alert lifecycle status. */
export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const tone = statusTone(status);
  return (
    <Badge dot live={status === 'active'} className={cn(tone.text, tone.bg, tone.border, className)}>
      {tone.label}
    </Badge>
  );
}

/** System-event level, on the same visual scale. */
export function EventLevelBadge({ level, className }: { level: string; className?: string }) {
  const tone = eventLevelTone(level);
  return (
    <Badge dot className={cn(tone.text, tone.bg, tone.border, className)}>
      {level}
    </Badge>
  );
}

/**
 * Bare status LED with an optional expanding ring.
 *
 * Used in the top bar and panel headers where a full pill would be too
 * heavy but the state still has to be visible at a glance across a room.
 */
export function StatusLed({
  tone,
  pulse = false,
  className,
}: {
  /** Background colour class, e.g. `bg-safe`. */
  tone: string;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span className={cn('relative inline-flex h-2 w-2 shrink-0', className)}>
      {pulse ? (
        <span
          className={cn('absolute inset-0 rounded-full opacity-60 animate-ring-out', tone)}
          aria-hidden
        />
      ) : null}
      <span className={cn('relative inline-flex h-2 w-2 rounded-full', tone)} />
    </span>
  );
}
