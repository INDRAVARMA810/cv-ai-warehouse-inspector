import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, RefreshCw, ServerCrash, WifiOff } from 'lucide-react';
import { ApiError } from '@/services';
import { Button } from './Button';
import { cn } from '@/utils/cn';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}

/** Shown when a query succeeds but matches nothing. */
export function EmptyState({
  title,
  description,
  icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn('flex flex-col items-center justify-center px-6 py-16 text-center', className)}
    >
      <span className="grid h-12 w-12 place-items-center rounded-xl border border-surface-700 bg-surface-800 text-content-muted">
        {icon ?? <Inbox className="h-5 w-5" />}
      </span>
      <h3 className="mt-4 text-sm font-semibold text-content-primary">{title}</h3>
      {description ? (
        <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-content-muted">{description}</p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
  /** Compact rendering for inline placement inside a small panel. */
  compact?: boolean;
}

/**
 * Shown when a query fails.
 *
 * The copy adapts to the failure: an unreachable API, a database
 * outage and a client error each call for different operator action, so
 * lumping them into one "something went wrong" would waste the
 * diagnostic detail the backend already provides.
 */
export function ErrorState({ error, onRetry, className, compact = false }: ErrorStateProps) {
  const apiError = error instanceof ApiError ? error : null;

  const { icon, title, description } = describeError(apiError, error);

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/5 p-4',
          className,
        )}
      >
        <span className="mt-0.5 text-red-300">{icon}</span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-red-200">{title}</p>
          <p className="mt-0.5 text-xs text-content-muted">{description}</p>
        </div>
        {onRetry ? (
          <Button size="sm" variant="ghost" icon={<RefreshCw className="h-3.5 w-3.5" />} onClick={onRetry}>
            Retry
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div
      className={cn('flex flex-col items-center justify-center px-6 py-16 text-center', className)}
    >
      <span className="grid h-12 w-12 place-items-center rounded-xl border border-red-500/30 bg-red-500/10 text-red-300">
        {icon}
      </span>
      <h3 className="mt-4 text-sm font-semibold text-content-primary">{title}</h3>
      <p className="mt-1.5 max-w-md text-xs leading-relaxed text-content-muted">{description}</p>

      {apiError && apiError.fieldErrors.length > 0 ? (
        <ul className="mt-4 space-y-1 text-left text-xs text-content-muted">
          {apiError.fieldErrors.map((fieldError) => (
            <li key={fieldError.field}>
              <span className="font-mono text-content-secondary">{fieldError.field}</span>
              {': '}
              {fieldError.message}
            </li>
          ))}
        </ul>
      ) : null}

      {onRetry ? (
        <Button
          className="mt-5"
          variant="primary"
          icon={<RefreshCw className="h-4 w-4" />}
          onClick={onRetry}
        >
          Try again
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
      icon: <WifiOff className="h-5 w-5" />,
      title: 'Cannot reach the API',
      description:
        'The dashboard could not contact the safety platform. Confirm the backend is running and reachable, then retry.',
    };
  }

  if (apiError?.kind === 'unavailable') {
    return {
      icon: <ServerCrash className="h-5 w-5" />,
      title: 'Platform temporarily unavailable',
      description:
        apiError.message ||
        'The database backing the platform is unavailable. This is usually temporary — retry shortly.',
    };
  }

  if (apiError?.kind === 'timeout') {
    return {
      icon: <RefreshCw className="h-5 w-5" />,
      title: 'Request timed out',
      description: 'The server took too long to respond. It may be under load.',
    };
  }

  if (apiError?.kind === 'server') {
    return {
      icon: <ServerCrash className="h-5 w-5" />,
      title: 'Server error',
      description: apiError.message || 'The platform returned an unexpected error.',
    };
  }

  return {
    icon: <AlertTriangle className="h-5 w-5" />,
    title: 'Unable to load data',
    description:
      apiError?.message ??
      (raw instanceof Error ? raw.message : 'An unexpected error occurred.'),
  };
}
