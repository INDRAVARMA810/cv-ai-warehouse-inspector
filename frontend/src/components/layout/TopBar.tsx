import { useEffect, useState } from 'react';
import { Menu, RefreshCw } from 'lucide-react';
import { useHealth } from '@/hooks';
import { cn } from '@/utils/cn';
import { IconButton } from '@/components/ui';

interface TopBarProps {
  title: string;
  subtitle?: string;
  onOpenNav: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

/**
 * Page header with live platform status.
 *
 * The connection indicator polls independently of whatever the page is
 * doing, so an operator can always tell whether what they are looking
 * at is live — a stale dashboard that looks healthy is worse than one
 * that admits it is disconnected.
 */
export function TopBar({
  title,
  subtitle,
  onOpenNav,
  onRefresh,
  isRefreshing = false,
}: TopBarProps) {
  const { data: health, isError } = useHealth();
  const clock = useClock();

  const state = isError
    ? { label: 'Disconnected', dot: 'bg-red-400', text: 'text-red-300' }
    : health?.status === 'ok'
      ? { label: 'Live', dot: 'bg-emerald-400', text: 'text-emerald-300' }
      : health?.status === 'degraded'
        ? { label: 'Degraded', dot: 'bg-amber-400', text: 'text-amber-300' }
        : { label: 'Connecting', dot: 'bg-slate-400', text: 'text-content-muted' };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-surface-700/70 bg-surface-900/85 px-4 backdrop-blur-md sm:px-6">
      <IconButton
        label="Open navigation"
        icon={<Menu className="h-4 w-4" />}
        onClick={onOpenNav}
        className="lg:hidden"
      />

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold leading-tight text-content-primary">
          {title}
        </h1>
        {subtitle ? (
          <p className="truncate text-xs leading-tight text-content-muted">{subtitle}</p>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <span
          className={cn(
            'hidden items-center gap-2 rounded-lg border border-surface-700 bg-surface-850 px-2.5 py-1.5 sm:inline-flex',
            state.text,
          )}
        >
          <span className="relative flex h-2 w-2">
            {state.label === 'Live' ? (
              <span
                className={cn('absolute inline-flex h-full w-full rounded-full opacity-60', state.dot, 'animate-pulse-ring')}
              />
            ) : null}
            <span className={cn('relative inline-flex h-2 w-2 rounded-full', state.dot)} />
          </span>
          <span className="text-xs font-medium">{state.label}</span>
        </span>

        <span className="hidden font-mono text-xs tabular-nums text-content-muted md:inline">
          {clock}
        </span>

        {onRefresh ? (
          <IconButton
            label="Refresh data"
            variant="secondary"
            onClick={onRefresh}
            icon={<RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />}
          />
        ) : null}
      </div>
    </header>
  );
}

/** Ticking wall clock, updated once per second. */
function useClock(): string {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return now.toLocaleTimeString(undefined, { hour12: false });
}
