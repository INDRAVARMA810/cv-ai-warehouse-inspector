import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell,
  Camera,
  Cpu,
  Gauge,
  Menu,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAlerts, useHealth, useStreamStatus } from '@/hooks';
import { cn } from '@/utils/cn';
import { formatRelative, truncate } from '@/utils/format';
import { levelTone } from '@/utils/severity';
import { Badge, IconButton, StatusLed } from '@/components/ui';

interface TopBarProps {
  title: string;
  subtitle?: string;
  onOpenNav: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

/**
 * Global status bar.
 *
 * Carries the six readings an operator must be able to see without
 * navigating anywhere: overall health, AI pipeline, camera, GPU, frame
 * rate and time. Each is an independent poll, so one failing subsystem
 * greys only its own readout instead of blanking the row.
 */
export function TopBar({
  title,
  subtitle,
  onOpenNav,
  onRefresh,
  isRefreshing = false,
}: TopBarProps) {
  const health = useHealth();
  const stream = useStreamStatus();
  const clock = useClock();

  const info = stream.data;
  const dbHealthy = health.data?.components.find((c) => c.name === 'database')?.healthy ?? false;

  // Overall health as a single percentage: an operator wants one number
  // first, and the breakdown only when that number is not 100.
  const score = useMemo(() => {
    const signals = [
      health.isSuccess && health.data?.status === 'ok',
      dbHealthy,
      Boolean(info?.running),
      Boolean(info?.available),
    ];
    const met = signals.filter(Boolean).length;
    return Math.round((met / signals.length) * 100);
  }, [health.isSuccess, health.data, dbHealthy, info]);

  const scoreTone = score >= 100 ? 'safe' : score >= 50 ? 'warn' : 'crit';

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-edge bg-panel/95 px-3 backdrop-blur-md sm:px-4">
      <IconButton
        label="Open navigation"
        icon={<Menu className="h-4 w-4" />}
        onClick={onOpenNav}
        className="lg:hidden"
      />

      <div className="min-w-0 shrink">
        <h1 className="truncate text-sm font-semibold leading-tight text-ink">{title}</h1>
        {subtitle ? (
          <p className="truncate text-2xs leading-tight text-ink-ghost">{subtitle}</p>
        ) : null}
      </div>

      {/* Instrument cluster */}
      <div className="ml-auto flex items-center gap-1.5 overflow-x-auto">
        <HealthScore score={score} tone={scoreTone} loading={health.isLoading} />

        <span className="hidden h-6 w-px bg-edge md:block" />

        <Readout
          icon={Sparkles}
          label="AI"
          value={info?.running ? 'ACTIVE' : 'IDLE'}
          tone={info?.running ? 'safe' : 'neutral'}
          loading={stream.isLoading}
          className="hidden md:flex"
        />
        <Readout
          icon={Camera}
          label="CAM"
          value={info?.available ? 'LIVE' : info?.running ? 'SYNC' : 'OFF'}
          tone={info?.available ? 'safe' : info?.running ? 'warn' : 'neutral'}
          loading={stream.isLoading}
          pulse={info?.available}
          className="hidden md:flex"
        />
        <Readout
          icon={Cpu}
          label="GPU"
          value={(info?.device ?? '––').toUpperCase()}
          tone={info?.device === 'cuda' ? 'safe' : info?.device ? 'info' : 'neutral'}
          loading={stream.isLoading}
          className="hidden lg:flex"
        />
        <Readout
          icon={Gauge}
          label="FPS"
          value={info?.publish_fps ? info.publish_fps.toFixed(1) : '––'}
          tone={
            !info?.publish_fps ? 'neutral' : info.publish_fps >= 10 ? 'safe' : 'warn'
          }
          loading={stream.isLoading}
          className="hidden lg:flex"
        />

        <span className="hidden h-6 w-px bg-edge lg:block" />

        <time className="hidden font-mono text-xs tabular text-ink-dim xl:block" dateTime={clock}>
          {clock}
        </time>

        {onRefresh ? (
          <IconButton
            size="sm"
            label="Refresh data"
            variant="secondary"
            onClick={onRefresh}
            icon={<RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />}
          />
        ) : null}

        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  );
}

/** Aggregate health as a single percentage with a segmented gauge. */
function HealthScore({
  score,
  tone,
  loading,
}: {
  score: number;
  tone: 'safe' | 'warn' | 'crit';
  loading: boolean;
}) {
  const colour = tone === 'safe' ? 'bg-safe' : tone === 'warn' ? 'bg-warn' : 'bg-crit';
  const text = tone === 'safe' ? 'text-safe' : tone === 'warn' ? 'text-warn' : 'text-crit';
  const segments = 5;
  const lit = Math.round((score / 100) * segments);

  return (
    <div
      className="flex items-center gap-2 rounded-control border border-edge bg-panel-inset px-2 py-1"
      title={`System health ${score}%`}
    >
      <ShieldCheck className={cn('h-3.5 w-3.5 shrink-0', loading ? 'text-ink-ghost' : text)} />
      <div className="hidden flex-col gap-1 sm:flex">
        <span className="font-mono text-2xs leading-none tabular text-ink-faint">
          HEALTH{' '}
          <span className={cn('font-semibold', loading ? 'text-ink-ghost' : text)}>
            {loading ? '––' : `${score}%`}
          </span>
        </span>
        <span className="flex gap-0.5" aria-hidden>
          {Array.from({ length: segments }).map((_, index) => (
            <span
              key={index}
              className={cn(
                'h-1 w-3 rounded-[1px] transition-colors duration-300',
                !loading && index < lit ? colour : 'bg-edge-strong',
              )}
            />
          ))}
        </span>
      </div>
    </div>
  );
}

/** One compact labelled instrument reading. */
function Readout({
  icon: Icon,
  label,
  value,
  tone,
  loading,
  pulse,
  className,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone: 'safe' | 'warn' | 'crit' | 'info' | 'neutral';
  loading?: boolean;
  pulse?: boolean;
  className?: string;
}) {
  const tones = {
    safe: 'text-safe',
    warn: 'text-warn',
    crit: 'text-crit',
    info: 'text-info',
    neutral: 'text-ink-faint',
  } as const;

  return (
    <div
      className={cn(
        'flex items-center gap-1.5 rounded-control border border-edge bg-panel-inset px-2 py-1',
        className,
      )}
      title={`${label}: ${value}`}
    >
      <Icon className={cn('h-3.5 w-3.5 shrink-0', loading ? 'text-ink-ghost' : tones[tone])} />
      <div className="flex flex-col leading-none">
        <span className="font-mono text-[9px] uppercase tracking-wider text-ink-ghost">
          {label}
        </span>
        <span
          className={cn(
            'mt-0.5 font-mono text-2xs font-semibold tabular leading-none',
            loading ? 'text-ink-ghost' : tones[tone],
            pulse && 'animate-ticker',
          )}
        >
          {loading ? '––' : value}
        </span>
      </div>
    </div>
  );
}

/** Notification bell backed by the live active-alert query. */
function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useAlerts(
    { page: 1, page_size: 6, status: 'active', sort_by: 'occurred_at', order: 'desc' },
    30_000,
  );

  const alerts = data?.items ?? [];
  const count = data?.meta.total ?? 0;

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={`Notifications (${count} active)`}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          'relative grid h-8 w-8 place-items-center rounded-control border transition-colors duration-150',
          count > 0
            ? 'border-crit/40 bg-crit/10 text-crit hover:bg-crit/20'
            : 'border-edge bg-panel-raised text-ink-faint hover:text-ink',
        )}
      >
        <Bell className="h-3.5 w-3.5" />
        {count > 0 ? (
          <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full border border-panel bg-crit px-0.5 font-mono text-[9px] font-bold tabular text-void">
            {count > 9 ? '9+' : count}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 top-10 z-50 w-80 animate-rise-in overflow-hidden rounded-panel border border-edge bg-panel shadow-panel">
          <div className="flex items-center justify-between border-b border-edge bg-panel-rail px-3 py-2">
            <span className="eyebrow">Active Alerts</span>
            <Badge>{count}</Badge>
          </div>

          {isLoading ? (
            <p className="px-3 py-6 text-center text-2xs text-ink-faint">Loading…</p>
          ) : alerts.length === 0 ? (
            <div className="px-3 py-6 text-center">
              <ShieldCheck className="mx-auto h-5 w-5 text-safe" />
              <p className="mt-2 text-2xs text-ink-dim">All clear</p>
              <p className="text-2xs text-ink-ghost">No alerts need attention</p>
            </div>
          ) : (
            <ul className="max-h-72 overflow-y-auto">
              {alerts.map((alert) => {
                const tone = levelTone(alert.level);
                return (
                  <li key={alert.alert_id}>
                    <Link
                      to={`/alerts?focus=${alert.alert_id}`}
                      onClick={() => setOpen(false)}
                      className={cn(
                        'block border-b border-edge-soft px-3 py-2 transition-colors hover:bg-panel-raised',
                        tone.rail,
                      )}
                    >
                      <p className="text-2xs leading-snug text-ink">
                        {truncate(alert.message, 62)}
                      </p>
                      <p className="mt-0.5 flex items-center gap-1.5 font-mono text-2xs text-ink-ghost">
                        <span className={tone.text}>{tone.label}</span>
                        <span>·</span>
                        <span>{formatRelative(alert.occurred_at)}</span>
                      </p>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}

          <Link
            to="/alerts?status=active"
            onClick={() => setOpen(false)}
            className="block border-t border-edge bg-panel-rail px-3 py-2 text-center text-2xs font-medium text-info transition-colors hover:bg-edge-soft"
          >
            View all alerts
          </Link>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Operator profile.
 *
 * Static: the platform has no authentication yet, so this identifies the
 * shift rather than a signed-in user. It is a placeholder for the real
 * session once auth exists.
 */
function UserMenu() {
  return (
    <div
      className="flex items-center gap-2 rounded-control border border-edge bg-panel-inset py-1 pl-1 pr-2"
      title="Signed-in operator (authentication not yet enabled)"
    >
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-control bg-edge-strong text-ink-dim">
        <UserRound className="h-3.5 w-3.5" />
      </span>
      <div className="hidden flex-col leading-none xl:flex">
        <span className="text-2xs font-medium text-ink-dim">Control Room</span>
        <span className="font-mono text-[9px] uppercase tracking-wider text-ink-ghost">
          Shift A
        </span>
      </div>
      <StatusLed tone="bg-safe" className="hidden xl:inline-flex" />
    </div>
  );
}

/** Wall clock, second resolution. */
function useClock(): string {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return now.toLocaleTimeString(undefined, { hour12: false });
}
