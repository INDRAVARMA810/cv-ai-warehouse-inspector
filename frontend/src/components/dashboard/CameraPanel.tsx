import { AlertTriangle, Cpu, Loader2, RefreshCw, Radio, VideoOff } from 'lucide-react';
import type { SystemEvent } from '@/types';
import { useMjpegStream, useStreamStatus } from '@/hooks';
import { formatDateTime, formatRelative, humanise } from '@/utils/format';
import { cn } from '@/utils/cn';
import { Button, Panel, PanelHeader } from '@/components/ui';

interface CameraPanelProps {
  events: SystemEvent[];
  isLoading?: boolean;
}

/**
 * Live annotated video feed.
 *
 * Renders the backend's MJPEG stream directly in an `<img>`; the
 * browser decodes `multipart/x-mixed-replace` natively, so no
 * client-side video code is involved. Connection lifecycle, backoff and
 * reconnection live in `useMjpegStream`, leaving this component
 * presentational.
 */
export function CameraPanel({ events, isLoading = false }: CameraPanelProps) {
  const stream = useMjpegStream({ fps: 15 });
  const status = useStreamStatus();

  const info = status.data;
  const badge = describeConnection(stream.state, info?.available);

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        title="Live Feed"
        description="Annotated detection stream"
        icon={<Radio className="h-4 w-4" />}
        actions={
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium',
                badge.tone,
              )}
            >
              <span className="relative flex h-1.5 w-1.5">
                {stream.state === 'live' ? (
                  <span
                    className={cn(
                      'absolute inline-flex h-full w-full rounded-full opacity-70',
                      badge.dot,
                      'animate-pulse-ring',
                    )}
                  />
                ) : null}
                <span className={cn('relative inline-flex h-1.5 w-1.5 rounded-full', badge.dot)} />
              </span>
              {badge.label}
            </span>
            <Button
              size="sm"
              variant="ghost"
              icon={<RefreshCw className="h-3.5 w-3.5" />}
              onClick={stream.reconnect}
              aria-label="Reconnect stream"
            >
              <span className="sr-only sm:not-sr-only">Reconnect</span>
            </Button>
          </div>
        }
      />

      {/* Viewport */}
      <div className="relative aspect-video w-full overflow-hidden border-b border-surface-700/70 bg-surface-950">
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.18]"
          style={{
            backgroundImage:
              'linear-gradient(#22303F 1px, transparent 1px), linear-gradient(90deg, #22303F 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        {stream.src ? (
          <img
            key={stream.src}
            src={stream.src}
            alt="Live annotated detection feed"
            onLoad={stream.onLoad}
            onError={stream.onError}
            className={cn(
              'absolute inset-0 h-full w-full object-contain transition-opacity duration-300',
              stream.state === 'live' ? 'opacity-100' : 'opacity-0',
            )}
          />
        ) : null}

        {stream.state !== 'live' ? (
          <div className="absolute inset-0 grid place-items-center px-6 text-center">
            <StreamOverlay
              state={stream.state}
              attempt={stream.attempt}
              retryInMs={stream.retryInMs}
              detail={info?.error ?? null}
              onRetry={stream.reconnect}
            />
          </div>
        ) : null}

        {/* Corner registration marks */}
        {(
          [
            'left-3 top-3 border-l-2 border-t-2',
            'right-3 top-3 border-r-2 border-t-2',
            'left-3 bottom-3 border-l-2 border-b-2',
            'right-3 bottom-3 border-r-2 border-b-2',
          ] as const
        ).map((position) => (
          <span
            key={position}
            aria-hidden
            className={cn('absolute h-4 w-4 border-surface-600', position)}
          />
        ))}
      </div>

      {/* Stream facts */}
      <dl className="grid grid-cols-2 divide-x divide-surface-700/60 border-b border-surface-700/60 sm:grid-cols-4">
        <MetaCell
          label="Rate"
          value={info?.publish_fps ? `${info.publish_fps.toFixed(1)} fps` : '—'}
        />
        <MetaCell
          label="Resolution"
          value={
            info?.frame_width && info?.frame_height
              ? `${info.frame_width}×${info.frame_height}`
              : '—'
          }
        />
        <MetaCell
          label="Device"
          value={info?.device?.toUpperCase() ?? '—'}
          icon={<Cpu className="h-3 w-3" />}
        />
        <MetaCell label="Viewers" value={info ? String(info.viewers) : '—'} />
      </dl>

      <PipelineFooter events={events} isLoading={isLoading} />
    </Panel>
  );
}

/** Overlay shown whenever the picture is not live. */
function StreamOverlay({
  state,
  attempt,
  retryInMs,
  detail,
  onRetry,
}: {
  state: 'connecting' | 'reconnecting' | 'error';
  attempt: number;
  retryInMs: number | null;
  detail: string | null;
  onRetry: () => void;
}) {
  if (state === 'error') {
    return (
      <div className="max-w-sm">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl border border-red-500/30 bg-red-500/10 text-red-300">
          <VideoOff className="h-5 w-5" />
        </span>
        <p className="mt-3 text-sm font-semibold text-content-primary">Stream unavailable</p>
        <p className="mt-1.5 text-xs leading-relaxed text-content-muted">
          {detail ??
            'The video source could not be reached after several attempts. Check that a camera or video file is configured for the backend.'}
        </p>
        <Button className="mt-4" variant="primary" icon={<RefreshCw className="h-4 w-4" />} onClick={onRetry}>
          Try again
        </Button>
      </div>
    );
  }

  if (state === 'reconnecting') {
    return (
      <div className="max-w-sm">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-300">
          <AlertTriangle className="h-5 w-5" />
        </span>
        <p className="mt-3 text-sm font-semibold text-content-primary">Reconnecting…</p>
        <p className="mt-1.5 text-xs text-content-muted">
          Attempt {attempt}
          {retryInMs ? ` · retrying in ${Math.round(retryInMs / 1000)}s` : ''}
        </p>
        <Button className="mt-4" size="sm" variant="secondary" onClick={onRetry}>
          Retry now
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-sm">
      <Loader2 className="mx-auto h-7 w-7 animate-spin text-accent" />
      <p className="mt-3 text-sm font-semibold text-content-primary">Connecting to feed…</p>
      <p className="mt-1.5 text-xs text-content-muted">
        Starting the capture pipeline and loading the detection model.
      </p>
    </div>
  );
}

function MetaCell({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="px-4 py-3">
      <dt className="text-[11px] uppercase tracking-wider text-content-muted">{label}</dt>
      <dd className="mt-1 flex items-center gap-1.5 truncate font-mono text-xs text-content-primary">
        {icon}
        <span className="truncate">{value}</span>
      </dd>
    </div>
  );
}

/** Latest pipeline-related system event, for context beneath the feed. */
function PipelineFooter({
  events,
  isLoading,
}: {
  events: SystemEvent[];
  isLoading: boolean;
}) {
  const latest = events.find((event) => /pipeline|camera|frame|model|zone/i.test(event.event_type));

  if (isLoading) {
    return (
      <div className="px-5 py-3">
        <p className="text-[11px] text-content-muted">Loading pipeline events…</p>
      </div>
    );
  }

  if (!latest) return null;

  return (
    <div className="px-5 py-3">
      <p className="truncate text-[11px] text-content-muted">
        <span className="text-content-secondary">{humanise(latest.event_type)}</span>
        {' · '}
        <span title={formatDateTime(latest.occurred_at)}>
          {formatRelative(latest.occurred_at)}
        </span>
        {latest.source ? <span className="font-mono"> · {latest.source}</span> : null}
      </p>
    </div>
  );
}

/** Map connection state onto badge copy and colour. */
function describeConnection(
  state: 'connecting' | 'live' | 'reconnecting' | 'error',
  available: boolean | undefined,
): { label: string; tone: string; dot: string } {
  switch (state) {
    case 'live':
      return {
        label: 'Live',
        tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
        dot: 'bg-emerald-400',
      };
    case 'reconnecting':
      return {
        label: 'Reconnecting',
        tone: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
        dot: 'bg-amber-400',
      };
    case 'error':
      return {
        label: 'Offline',
        tone: 'border-red-500/30 bg-red-500/10 text-red-300',
        dot: 'bg-red-400',
      };
    default:
      return {
        label: available === false ? 'Starting' : 'Connecting',
        tone: 'border-surface-600 bg-surface-700/40 text-content-muted',
        dot: 'bg-slate-400',
      };
  }
}
