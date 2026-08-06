import type { ReactNode } from 'react';
import {
  Boxes,
  Camera,
  Cpu,
  Database,
  Gauge,
  Radar,
  ScrollText,
  Server,
  ShieldQuestion,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useHealth, useStreamStatus } from '@/hooks';
import { cn } from '@/utils/cn';
import { formatDuration } from '@/utils/format';
import { ListSkeleton, Panel, PanelHeader, StatusLed } from '@/components/ui';

type SubsystemState = 'ok' | 'degraded' | 'down' | 'unknown';

interface Subsystem {
  key: string;
  label: string;
  icon: LucideIcon;
  state: SubsystemState;
  detail: string;
}

const STATE_STYLES: Record<SubsystemState, { dot: string; text: string; label: string; rail: string }> = {
  ok: { dot: 'bg-safe', text: 'text-safe', label: 'OPERATIONAL', rail: 'shadow-rail-safe' },
  degraded: { dot: 'bg-warn', text: 'text-warn', label: 'DEGRADED', rail: 'shadow-rail-warn' },
  down: { dot: 'bg-crit', text: 'text-crit', label: 'FAULT', rail: 'shadow-rail-crit' },
  unknown: { dot: 'bg-ink-ghost', text: 'text-ink-faint', label: 'UNKNOWN', rail: '' },
};

/**
 * Subsystem status board.
 *
 * Reports each dependency separately rather than collapsing to one
 * light: "degraded" is only actionable if an operator can see *which*
 * part is degraded.
 *
 * Only the database and the stream are directly observable through the
 * API. The inference subsystems are inferred from stream behaviour —
 * shown honestly as derived rather than dressed up as independent
 * probes the backend does not expose.
 */
export function SystemStatusPanel({ className }: { className?: string }) {
  const health = useHealth();
  const stream = useStreamStatus();

  const isLoading = health.isLoading || stream.isLoading;
  const info = stream.data;

  const apiUp = health.isSuccess;
  const dbUp = health.data?.components.find((c) => c.name === 'database')?.healthy ?? false;
  const streaming = Boolean(info?.available);
  const running = Boolean(info?.running);

  const subsystems: Subsystem[] = [
    {
      key: 'database',
      label: 'PostgreSQL',
      icon: Database,
      state: !apiUp ? 'unknown' : dbUp ? 'ok' : 'down',
      detail: dbUp ? 'Connection pool healthy' : 'Connection check failing',
    },
    {
      key: 'api',
      label: 'FastAPI',
      icon: Server,
      state: apiUp ? 'ok' : 'down',
      detail: apiUp
        ? `${health.data?.application ?? 'API'} v${health.data?.version ?? '–'}`
        : 'Service unreachable',
    },
    {
      key: 'yolo',
      label: 'YOLO Detector',
      icon: Boxes,
      state: !running ? 'unknown' : streaming ? 'ok' : 'degraded',
      detail: info?.device ? `Inference on ${info.device.toUpperCase()}` : 'Idle — no active stream',
    },
    {
      key: 'tracker',
      label: 'ByteTrack',
      icon: Radar,
      state: !running ? 'unknown' : streaming ? 'ok' : 'degraded',
      detail: streaming ? 'Assigning identities' : 'Awaiting frames',
    },
    {
      key: 'rules',
      label: 'Rule Engine',
      icon: ScrollText,
      state: !running ? 'unknown' : 'ok',
      detail: running ? 'Evaluating every frame' : 'Idle — no active stream',
    },
    {
      key: 'stream',
      label: 'MJPEG Stream',
      icon: Camera,
      state: !running ? 'down' : streaming ? 'ok' : 'degraded',
      detail: streaming
        ? `${info?.viewers ?? 0} viewer(s) · ${info?.publish_fps?.toFixed(1) ?? '0'} fps`
        : running
          ? 'Started, no frames yet'
          : 'Not running',
    },
  ];

  const faults = subsystems.filter((s) => s.state === 'down').length;
  const degraded = subsystems.filter((s) => s.state === 'degraded').length;

  return (
    <Panel className={cn('flex flex-col overflow-hidden', className)}>
      <PanelHeader
        title="System Health"
        subtitle={
          isLoading
            ? 'Polling subsystems…'
            : faults > 0
              ? `${faults} fault${faults === 1 ? '' : 's'}`
              : degraded > 0
                ? `${degraded} degraded`
                : 'All subsystems nominal'
        }
        icon={<ShieldQuestion className="h-3.5 w-3.5" />}
        rail={faults > 0 ? 'shadow-rail-crit' : degraded > 0 ? 'shadow-rail-warn' : 'shadow-rail-safe'}
        actions={
          <span className="font-mono text-2xs tabular text-ink-faint">
            {subsystems.filter((s) => s.state === 'ok').length}/{subsystems.length}
          </span>
        }
      />

      {isLoading ? (
        <ListSkeleton rows={4} />
      ) : (
        <ul className="flex-1">
          {subsystems.map((subsystem) => {
            const style = STATE_STYLES[subsystem.state];
            const Icon = subsystem.icon;

            return (
              <li
                key={subsystem.key}
                className={cn(
                  'flex items-center gap-2.5 border-b border-edge-soft px-3 py-2 transition-colors last:border-b-0 hover:bg-panel-raised',
                  style.rail,
                )}
              >
                <Icon className={cn('h-3.5 w-3.5 shrink-0', style.text)} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium text-ink">{subsystem.label}</p>
                  <p className="truncate text-2xs text-ink-ghost">{subsystem.detail}</p>
                </div>
                <span className={cn('flex shrink-0 items-center gap-1.5 font-mono text-2xs font-semibold', style.text)}>
                  <StatusLed tone={style.dot} pulse={subsystem.state === 'down'} />
                  <span className="hidden sm:inline">{style.label}</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}

      <div className="flex items-center justify-between border-t border-edge bg-panel-rail/40 px-3 py-1.5">
        <span className="flex items-center gap-1.5 font-mono text-2xs text-ink-ghost">
          <Cpu className="h-3 w-3" />
          {info?.device?.toUpperCase() ?? 'NO DEVICE'}
        </span>
        <span className="flex items-center gap-1.5 font-mono text-2xs tabular text-ink-ghost">
          <Gauge className="h-3 w-3" />
          {info?.uptime ? formatDuration(info.uptime) : '––'}
        </span>
      </div>
    </Panel>
  );
}

/** Small inline status chip reused by the analytics and settings pages. */
export function SubsystemChip({
  label,
  ok,
  icon,
}: {
  label: string;
  ok: boolean;
  icon?: ReactNode;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-control border px-1.5 py-0.5 font-mono text-2xs',
        ok ? 'border-safe/30 bg-safe/10 text-safe' : 'border-crit/30 bg-crit/10 text-crit',
      )}
    >
      {icon}
      {label}
    </span>
  );
}
