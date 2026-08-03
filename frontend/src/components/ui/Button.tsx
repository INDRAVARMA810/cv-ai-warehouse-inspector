import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { cn } from '@/utils/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant?: Variant;
  size?: Size;
  /** Leading icon; sized by the button rather than the caller. */
  icon?: ReactNode;
  /** Shows a spinner and blocks interaction. */
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-accent/15 text-accent border-accent/40 hover:bg-accent/25 hover:border-accent/60',
  secondary:
    'bg-surface-750 text-content-primary border-surface-600 hover:bg-surface-700 hover:border-surface-600',
  ghost:
    'bg-transparent text-content-secondary border-transparent hover:bg-surface-750 hover:text-content-primary',
  danger:
    'bg-red-500/10 text-red-300 border-red-500/40 hover:bg-red-500/20 hover:border-red-500/60',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-2.5 text-xs gap-1.5',
  md: 'h-9 px-3.5 text-sm gap-2',
};

/** Standard action button. */
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
        'inline-flex select-none items-center justify-center rounded-lg border font-medium',
        'transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-900',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon
      )}
      {children}
    </button>
  );
}

interface IconButtonProps extends ComponentPropsWithoutRef<'button'> {
  /** Required: icon-only controls need an accessible name. */
  label: string;
  icon: ReactNode;
  variant?: Variant;
}

/** Square icon-only button. */
export function IconButton({
  label,
  icon,
  variant = 'ghost',
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
        'inline-grid h-8 w-8 place-items-center rounded-lg border transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
        'disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        className,
      )}
    >
      {icon}
    </button>
  );
}
