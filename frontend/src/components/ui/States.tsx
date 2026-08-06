import type { ReactNode } from 'react';
import {
  CircleOff,
  PlugZap,
  RefreshCw,
  ServerCrash,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';
import { ApiError } from '@/services';
import { Button } from './Button';
import { cn } from '@/utils/cn';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  /** Emerald treatment — an empty result that is good news. */
  positive?: boolean;
  className?: string;
}

/**
 * Shown when a query succeeds but matches nothing.
 *
 * The `positive` flag matters in a safety product: zero active alerts is
 * good news and should look like it, whereas an empty search result is
 * merely neutral. Rendering both identically would waste the strongest
 * signal the interface has.
 */
export function EmptyState({
  title,
  description,
  icon,
  action,
  positive = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex animate-rise-in flex-col items-center justify-center px-6 py-12 text-center',
        className,
      )}
    >
      <span
        className={cn(
          'grid h-10 w-10 place-items-center rounded-panel border',
          positive
            ? 'border-safe/30 bg-safe/10 text-safe'
            : 'border-edge bg-panel-inset text-ink-ghost',
        )}
      >
        {icon ??
          (positive ? <ShieldCheck className="h-4 w-4" /> : <CircleOff className="h-4 w-4" />)}
      </span>
      <h3 className="mt-3 text-sm font-medium text-ink">{title}</h3>
      {description ? (
        <p className="mt-1 max-w-xs text-2xs leading-relaxed text-ink-faint">{description}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
  /** Inline variant for placement inside a small panel. */
  compact?: boolean;
}

/**
 * Shown when a query fails.
 *
 * Copy adapts to the failure kind. An unreachable API, a database outage
 * and a client error each call for different operator action, so
 * collapsing them into one generic message would discard the diagnostic
 * detail the backend already provides.
 */
export function ErrorState({ error, onRetry, className, compact = false }: ErrorStateProps) {
  const apiError = error instanceof ApiError ? error : null;
  const { icon, title, description } = describeError(apiError, error);

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-start gap-2.5 rounded-panel border border-crit/30 bg-crit/5 p-3 shadow-rail-crit',
          className,
        )}
      >
        <span className="mt-0.5 shrink-0 text-crit">{icon}</span>
        <div className="min-w-0 flex-1">
          <p className="text-2xs font-semibold uppercase tracking-wider text-crit">{title}</p>
          <p className="mt-0.5 text-2xs text-ink-faint">{description}</p>
        </div>
        {onRetry ? (
          <Button
            size="sm"
            variant="ghost"
            icon={<RefreshCw className="h-3 w-3" />}
            onClick={onRetry}
          >
            Retry
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex animate-rise-in flex-col items-center justify-center px-6 py-12 text-center',
        className,
      )}
    >
      <span className="grid h-10 w-10 place-items-center rounded-panel border border-crit/30 bg-crit/10 text-crit">
        {icon}
      </span>
      <h3 className="mt-3 text-sm font-medium text-ink">{title}</h3>
      <p className="mt-1 max-w-sm text-2xs leading-relaxed text-ink-faint">{description}</p>

      {apiError && apiError.fieldErrors.length > 0 ? (
        <ul className="mt-3 space-y-0.5 text-left font-mono text-2xs text-ink-faint">
          {apiError.fieldErrors.map((fieldError) => (
            <li key={fieldError.field}>
              <span className="text-ink-dim">{fieldError.field}</span>
              {': '}
              {fieldError.message}
            </li>
          ))}
        </ul>
      ) : null}

      {onRetry ? (
        <Button
          className="mt-4"
          variant="primary"
          icon={<RefreshCw className="h-3.5 w-3.5" />}
          onClick={onRetry}
        >
          Retry
        </Button>
      ) : null}
    </div>
  );
}

/** Map a failure onto operator-facing copy and an icon. */
function describeError(
  apiError: ApiError | null,
  raw: unknown,
): { icon: ReactNode; title: string; description: string } {
  if (apiError?.kind === 'network') {
    return {
      icon: <PlugZap className="h-4 w-4" />,
      title: 'API unreachable',
      description:
        'The dashboard cannot contact the safety platform. Confirm the backend service is running, then retry.',
    };
  }
  if (apiError?.kind === 'unavailable') {
    return {
      icon: <ServerCrash className="h-4 w-4" />,
      title: 'Platform unavailable',
      description:
        apiError.message ||
        'The database backing the platform is unavailable. This is usually transient — retry shortly.',
    };
  }
  if (apiError?.kind === 'timeout') {
    return {
      icon: <RefreshCw className="h-4 w-4" />,
      title: 'Request timed out',
      description: 'The server took too long to respond. It may be under load.',
    };
  }
  if (apiError?.kind === 'server') {
    return {
      icon: <ServerCrash className="h-4 w-4" />,
      title: 'Server fault',
      description: apiError.message || 'The platform returned an unexpected error.',
    };
  }
  return {
    icon: <TriangleAlert className="h-4 w-4" />,
    title: 'Unable to load',
    description:
      apiError?.message ?? (raw instanceof Error ? raw.message : 'An unexpected error occurred.'),
  };
}
