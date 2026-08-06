import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { cn } from '@/utils/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'safe';
type Size = 'xs' | 'sm' | 'md';

interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant?: Variant;
  size?: Size;
  icon?: ReactNode;
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary: 'border-info/40 bg-info/12 text-info hover:border-info/60 hover:bg-info/20',
  secondary:
    'border-edge bg-panel-raised text-ink-dim hover:border-edge-strong hover:bg-edge-soft hover:text-ink',
  ghost: 'border-transparent bg-transparent text-ink-faint hover:bg-edge-soft hover:text-ink',
  danger: 'border-crit/40 bg-crit/10 text-crit hover:border-crit/60 hover:bg-crit/20',
  safe: 'border-safe/40 bg-safe/10 text-safe hover:border-safe/60 hover:bg-safe/20',
};

const SIZES: Record<Size, string> = {
  xs: 'h-6 px-2 text-2xs gap-1',
  sm: 'h-7 px-2.5 text-2xs gap-1.5',
  md: 'h-8 px-3 text-xs gap-1.5',
};

/** Control-panel button: tight radius, hairline border, no gloss. */
export function Button({
  variant = 'secondary',
  size = 'md',
  icon,
  loading = false,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      {...rest}
      className={cn(
        'inline-flex select-none items-center justify-center rounded-control border font-medium',
        'transition-colors duration-150 ease-instrument',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info/60',
        'disabled:cursor-not-allowed disabled:opacity-40',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {loading ? (
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}

interface IconButtonProps extends ComponentPropsWithoutRef<'button'> {
  /** Required: an icon-only control needs an accessible name. */
  label: string;
  icon: ReactNode;
  variant?: Variant;
  size?: Size;
}

/** Square icon-only control. */
export function IconButton({
  label,
  icon,
  variant = 'ghost',
  size = 'md',
  className,
  ...rest
}: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={cn(
        'inline-grid place-items-center rounded-control border transition-colors duration-150 ease-instrument',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-info/60',
        'disabled:cursor-not-allowed disabled:opacity-40',
        size === 'xs' ? 'h-6 w-6' : size === 'sm' ? 'h-7 w-7' : 'h-8 w-8',
        VARIANTS[variant],
        className,
      )}
    >
      {icon}
    </button>
  );
}
