import { Cpu, Radio, VideoOff } from 'lucide-react';
import type { SystemEvent } from '@/types';
import { formatDateTime, formatRelative, humanise } from '@/utils/format';
import { cn } from '@/utils/cn';
import { Panel, PanelHeader, Skeleton } from '@/components/ui';

interface CameraPanelProps {
  events: SystemEvent[];
  isLoading?: boolean;
}

/**
 * Live pipeline / camera panel.
 *
 * The platform exposes no video-streaming endpoint, so this deliberately
 * shows **no video**. Fabricating a feed would misrepresent a safety
 * system's actual coverage, which is the one thing an operator must be
 * able to trust. Instead the panel reports the real state of the capture
 * pipeline, derived from the system events the backend does publish.
 */
export function CameraPanel({ events, isLoading = false }: CameraPanelProps) {
  const status = derivePipelineStatus(events);

  return (
    <Panel className="overflow-hidden">
      <PanelHeader
        title="Live Pipeline"
        description="Capture and inference status"
        icon={<Radio className="h-4 w-4" />}
        actions={
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium',
              status.tone,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', status.dot)} />
            {status.label}
          </span>
        }
      />

      {/* Viewport */}
      <div className="relative aspect-video w-full border-b border-surface-700/70 bg-surface-950">
        {/* Alignment grid, purely decorative */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.18]"
          style={{
            backgroundImage:
              'linear-gradient(#22303F 1px, transparent 1px), linear-gradient(90deg, #22303F 1px, transparent 1px)',
            backgroundSize: '48px 48px',
          }}
        />

        <div className="absolute inset-0 grid place-items-center px-6 text-center">
          {isLoading ? (
            <Skeleton className="h-24 w-48" />
          ) : (
            <div className="max-w-sm">
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-xl border border-surface-700 bg-surface-850 text-content-muted">
                <VideoOff className="h-5 w-5" />
              </span>
              <p className="mt-3 text-sm font-semibold text-content-primary">
                No video stream endpoint
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-content-muted">
                The API exposes detections, tracks and alerts, but does not yet publish
                frames. Add an MJPEG or WebRTC endpoint to render the live feed here.
              </p>
            </div>
          )}
        </div>

        {/* Corner registration marks */}
        {(['left-3 top-3 border-l-2 border-t-2', 'right-3 top-3 border-r-2 border-t-2',
           'left-3 bottom-3 border-l-2 border-b-2', 'right-3 bottom-3 border-r-2 border-b-2'] as const).map(
          (position) => (
            <span
              key={position}
              aria-hidden
              className={cn('absolute h-4 w-4 border-surface-600', position)}
            />
          ),
        )}
      </div>

      {/* Real pipeline facts, from system events */}
      <dl className="grid grid-cols-2 divide-x divide-surface-700/60 border-b border-surface-700/60 sm:grid-cols-3 sm:divide-x">
        <MetaCell label="Last pipeline event" value={status.lastEventLabel} hint={status.lastEventAt} />
        <MetaCell label="Source" value={status.source ?? '—'} />
        <MetaCell
          label="Device"
          value={status.device ?? '—'}
          icon={<Cpu className="h-3 w-3" />}
          className="col-span-2 sm:col-span-1"
        />
      </dl>
    </Panel>
  );
}

function MetaCell({
  label,
  value,
  hint,
  icon,
  className,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('px-5 py-3.5', className)}>
      <dt className="text-[11px] uppercase tracking-wider text-content-muted">{label}</dt>
      <dd className="mt-1 flex items-center gap-1.5 truncate text-xs text-content-primary">
        {icon}
        <span className="truncate font-mono">{value}</span>
      </dd>
      {hint ? <p className="mt-0.5 truncate text-[11px] text-content-muted">{hint}</p> : null}
    </div>
  );
}

interface PipelineStatus {
  label: string;
  tone: string;
  dot: string;
  lastEventLabel: string;
  lastEventAt?: string;
  source: string | null;
  device: string | null;
}

/**
 * Infer capture state from the most recent pipeline-related events.
 *
 * Only facts the backend actually reported are used; anything unknown
 * stays blank rather than being guessed at.
 */
function derivePipelineStatus(events: SystemEvent[]): PipelineStatus {
  const pipelineEvents = events.filter((event) =>
    /pipeline|camera|frame|model|zone/i.test(event.event_type),
  );
  const latest = pipelineEvents[0] ?? events[0];

  const started = pipelineEvents.find((event) => /started/i.test(event.event_type));
  const dropped = pipelineEvents.find((event) => /drop|fail|lost/i.test(event.event_type));

  const device =
    (started?.metadata?.device as string | undefined) ??
    (latest?.metadata?.device as string | undefined) ??
    null;

  const stopped = pipelineEvents.find((event) => /stopped|shutdown/i.test(event.event_type));

  let label = 'Unknown';
  let tone = 'border-surface-600 bg-surface-700/40 text-content-muted';
  let dot = 'bg-slate-400';

  if (stopped) {
    label = 'Stopped';
    tone = 'border-surface-600 bg-surface-700/40 text-content-muted';
    dot = 'bg-slate-400';
  } else if (dropped) {
    label = 'Degraded';
    tone = 'border-amber-500/30 bg-amber-500/10 text-amber-300';
    dot = 'bg-amber-400';
  } else if (started) {
    label = 'Running';
    tone = 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300';
    dot = 'bg-emerald-400';
  }

  return {
    label,
    tone,
    dot,
    lastEventLabel: latest ? humanise(latest.event_type) : 'No events recorded',
    lastEventAt: latest
      ? `${formatRelative(latest.occurred_at)} · ${formatDateTime(latest.occurred_at)}`
      : undefined,
    source: latest?.source ?? null,
    device,
  };
}
