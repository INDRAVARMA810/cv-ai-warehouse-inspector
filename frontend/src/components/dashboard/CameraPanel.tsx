import { Cpu, Gauge, Maximize2, RefreshCw, ScanLine, Signal, VideoOff } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useMjpegStream, useStreamStatus } from '@/hooks';
import { cn } from '@/utils/cn';
import { formatDuration } from '@/utils/format';
import { Button, IconButton, Panel, PanelHeader, StatusLed } from '@/components/ui';

interface CameraPanelProps {
  /** Removes the header and chrome, for the full-screen monitoring view. */
  bare?: boolean;
  /** Requested frame rate. */
  fps?: number;
  className?: string;
}

/**
 * Live annotated camera feed.
 *
 * Renders the backend MJPEG stream directly in an `<img>` — the browser
 * decodes `multipart/x-mixed-replace` natively, so no client-side video
 * code is involved. Bounding boxes, track IDs, danger zones and the
 * violation overlay are burned in by the pipeline, so what an operator
 * sees here is exactly what the detector saw.
 *
 * Connection lifecycle, backoff and reconnection live in
 * `useMjpegStream`; this component is presentational.
 */
export function CameraPanel({ bare = false, fps = 15, className }: CameraPanelProps) {
  const stream = useMjpegStream({ fps });
  const status = useStreamStatus();
  const info = status.data;

  const state = stream.state;
  const badge =
    state === 'live'
      ? { label: 'LIVE', tone: 'text-safe', dot: 'bg-safe' }
      : state === 'reconnecting'
        ? { label: 'RECONNECT', tone: 'text-warn', dot: 'bg-warn' }
        : state === 'error'
          ? { label: 'OFFLINE', tone: 'text-crit', dot: 'bg-crit' }
          : { label: 'SYNC', tone: 'text-ink-faint', dot: 'bg-ink-ghost' };

  const viewport = (
    <div className="relative aspect-video w-full overflow-hidden well grid-backdrop">
      {stream.src ? (
        <img
          key={stream.src}
          src={stream.src}
          alt="Live annotated detection feed"
          onLoad={stream.onLoad}
          onError={stream.onError}
          className={cn(
            'absolute inset-0 h-full w-full object-contain transition-opacity duration-500',
            state === 'live' ? 'opacity-100' : 'opacity-0',
          )}
        />
      ) : null}

      {state !== 'live' ? (
        <div className="absolute inset-0 grid place-items-center px-6 text-center">
          <StreamOverlay
            state={state}
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
          'left-2 top-2 border-l border-t',
          'right-2 top-2 border-r border-t',
          'left-2 bottom-2 border-l border-b',
          'right-2 bottom-2 border-r border-b',
        ] as const
      ).map((position) => (
        <span
          key={position}
          aria-hidden
          className={cn('absolute h-3 w-3 border-edge-strong', position)}
        />
      ))}

      {/* Overlay HUD — mirrors the burned-in readout so the values stay
          legible even while the image is still fading in. */}
      {state === 'live' ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center gap-3 bg-gradient-to-t from-black/75 to-transparent px-3 pb-2 pt-6 font-mono text-2xs tabular">
          <span className="flex items-center gap-1.5 text-safe">
            <StatusLed tone="bg-safe" pulse />
            LIVE
          </span>
          {info?.publish_fps ? (
            <span className="flex items-center gap-1 text-ink-dim">
              <Gauge className="h-3 w-3" />
              {info.publish_fps.toFixed(1)} FPS
            </span>
          ) : null}
          {info?.device ? (
            <span className="flex items-center gap-1 text-ink-dim">
              <Cpu className="h-3 w-3" />
              {info.device.toUpperCase()}
            </span>
          ) : null}
          {info?.frame_width ? (
            <span className="ml-auto text-ink-faint">
              {info.frame_width}×{info.frame_height}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );

  if (bare) return <div className={className}>{viewport}</div>;

  return (
    <Panel className={cn('overflow-hidden', className)}>
      <PanelHeader
        title="Live Camera Feed"
        subtitle={info?.source ? shortSource(info.source) : 'Detection stream'}
        icon={<ScanLine className="h-3.5 w-3.5" />}
        actions={
          <>
            <span
              className={cn(
                'flex items-center gap-1.5 rounded-control border border-edge bg-panel-inset px-1.5 py-0.5 font-mono text-2xs font-semibold',
                badge.tone,
              )}
            >
              <StatusLed tone={badge.dot} pulse={state === 'live'} />
              {badge.label}
            </span>
            <IconButton
              size="sm"
              label="Reconnect stream"
              icon={<RefreshCw className="h-3 w-3" />}
              onClick={stream.reconnect}
            />
            <Link to="/live" aria-label="Open full-screen monitoring">
              <IconButton
                size="sm"
                label="Full screen"
                variant="secondary"
                icon={<Maximize2 className="h-3 w-3" />}
              />
            </Link>
          </>
        }
      />

      {viewport}

      <dl className="grid grid-cols-2 divide-x divide-edge border-t border-edge sm:grid-cols-4">
        <Cell label="Frame rate" value={info?.publish_fps ? `${info.publish_fps.toFixed(1)}` : '––'} unit="fps" />
        <Cell
          label="Resolution"
          value={info?.frame_width ? `${info.frame_width}×${info.frame_height}` : '––'}
        />
        <Cell label="Device" value={info?.device?.toUpperCase() ?? '––'} />
        <Cell
          label="Uptime"
          value={info?.uptime ? formatDuration(info.uptime) : '––'}
        />
      </dl>
    </Panel>
  );
}

function Cell({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="px-3 py-2">
      <dt className="eyebrow truncate">{label}</dt>
      <dd className="mt-0.5 truncate font-mono text-xs tabular text-ink">
        {value}
        {unit ? <span className="ml-1 text-ink-ghost">{unit}</span> : null}
      </dd>
    </div>
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
      <div className="max-w-sm animate-rise-in">
        <span className="mx-auto grid h-10 w-10 place-items-center rounded-panel border border-crit/30 bg-crit/10 text-crit">
          <VideoOff className="h-4 w-4" />
        </span>
        <p className="mt-3 text-sm font-medium text-ink">Camera offline</p>
        <p className="mt-1 text-2xs leading-relaxed text-ink-faint">
          {detail ??
            'No frames after several attempts. Check that a camera or video source is configured for the backend.'}
        </p>
        <Button className="mt-3" variant="primary" size="sm" icon={<RefreshCw className="h-3 w-3" />} onClick={onRetry}>
          Reconnect
        </Button>
      </div>
    );
  }

  if (state === 'reconnecting') {
    return (
      <div className="max-w-sm animate-rise-in">
        <span className="mx-auto grid h-10 w-10 place-items-center rounded-panel border border-warn/30 bg-warn/10 text-warn">
          <Signal className="h-4 w-4 animate-led-pulse" />
        </span>
        <p className="mt-3 text-sm font-medium text-ink">Reconnecting</p>
        <p className="mt-1 font-mono text-2xs tabular text-ink-faint">
          Attempt {attempt}
          {retryInMs ? ` · retry in ${Math.round(retryInMs / 1000)}s` : ''}
        </p>
        <Button className="mt-3" size="sm" onClick={onRetry}>
          Retry now
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-sm">
      <div className="mx-auto flex h-10 w-10 items-center justify-center">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-edge-strong border-t-info" />
      </div>
      <p className="mt-3 text-sm font-medium text-ink">Acquiring feed</p>
      <p className="mt-1 text-2xs text-ink-faint">
        Starting capture pipeline and loading the detection model.
      </p>
    </div>
  );
}

/** Trim a long source path to something that fits a subtitle. */
function shortSource(source: string): string {
  if (source.length <= 34) return source;
  const parts = source.split(/[/\\]/);
  return `…/${parts[parts.length - 1]}`;
}
