import { Cpu, Database, Info, Camera, Server, ShieldAlert, Sliders } from 'lucide-react';
import { useHealth, useStreamStatus } from '@/hooks';
import { AppLayout } from '@/components/layout';
import { Badge, Panel, PanelBody, PanelHeader, SectionHeading, StatusLed } from '@/components/ui';
import { formatDuration } from '@/utils/format';
import { cn } from '@/utils/cn';

/**
 * Runtime configuration, read-only.
 *
 * Every value here is set through backend environment variables and is
 * surfaced so an operator can confirm what the platform is *actually*
 * running with. Nothing is editable: the API exposes no configuration
 * write endpoints, and offering controls that silently do nothing would
 * be worse than showing none.
 */
export function SettingsPage() {
  const health = useHealth();
  const stream = useStreamStatus();
  const info = stream.data;

  return (
    <AppLayout
      title="Settings"
      subtitle="Runtime configuration"
      onRefresh={() => {
        void health.refetch();
        void stream.refetch();
      }}
      isRefreshing={health.isFetching || stream.isFetching}
    >
      <div className="max-w-4xl space-y-5">
        <div className="flex items-start gap-2.5 rounded-panel border border-info/25 bg-info/[0.06] p-3">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-info" />
          <p className="text-2xs leading-relaxed text-ink-dim">
            These values are read from the running services. Change them via backend environment
            variables (see <span className="font-mono text-ink">.env</span>) and restart the stack —
            the API exposes no configuration write endpoints.
          </p>
        </div>

        <section>
          <SectionHeading title="Application" />
          <Panel>
            <PanelHeader title="Service" icon={<Server className="h-3.5 w-3.5" />} />
            <PanelBody className="p-0">
              <Row label="Application" value={health.data?.application ?? '––'} />
              <Row label="Version" value={health.data?.version ?? '––'} mono />
              <Row
                label="Overall status"
                value={health.data?.status?.toUpperCase() ?? '––'}
                tone={health.data?.status === 'ok' ? 'safe' : 'crit'}
              />
            </PanelBody>
          </Panel>
        </section>

        <section>
          <SectionHeading title="Subsystems" />
          <Panel>
            <PanelHeader title="Component health" icon={<Database className="h-3.5 w-3.5" />} />
            <PanelBody className="p-0">
              {(health.data?.components ?? []).map((component) => (
                <Row
                  key={component.name}
                  label={component.name}
                  value={component.healthy ? 'OPERATIONAL' : 'FAULT'}
                  tone={component.healthy ? 'safe' : 'crit'}
                  hint={component.detail ?? undefined}
                />
              ))}
              {(health.data?.components.length ?? 0) === 0 ? (
                <p className="px-3 py-6 text-center text-2xs text-ink-ghost">
                  Component health unavailable
                </p>
              ) : null}
            </PanelBody>
          </Panel>
        </section>

        <section>
          <SectionHeading title="Video Pipeline" />
          <Panel>
            <PanelHeader title="Stream configuration" icon={<Camera className="h-3.5 w-3.5" />} />
            <PanelBody className="p-0">
              <Row label="Source" value={info?.source ?? '––'} mono />
              <Row
                label="Auto-start"
                value={info?.auto_start ? 'ENABLED' : 'DISABLED'}
                tone={info?.auto_start ? 'safe' : 'neutral'}
                hint="Starts capture when the first viewer connects"
              />
              <Row
                label="Running"
                value={info?.running ? 'YES' : 'NO'}
                tone={info?.running ? 'safe' : 'neutral'}
              />
              <Row
                label="Resolution"
                value={
                  info?.frame_width ? `${info.frame_width} × ${info.frame_height}` : '––'
                }
                mono
              />
              <Row label="JPEG quality" value={info ? String(info.jpeg_quality) : '––'} mono />
              <Row
                label="Uptime"
                value={info?.uptime ? formatDuration(info.uptime) : '––'}
                mono
              />
              {info?.error ? (
                <Row label="Last error" value={info.error} tone="crit" />
              ) : null}
            </PanelBody>
          </Panel>
        </section>

        <section>
          <SectionHeading title="Inference" />
          <Panel>
            <PanelHeader title="Detection device" icon={<Cpu className="h-3.5 w-3.5" />} />
            <PanelBody className="p-0">
              <Row
                label="Device"
                value={info?.device?.toUpperCase() ?? '––'}
                tone={info?.device === 'cuda' ? 'safe' : 'info'}
                hint={
                  info?.device === 'cuda'
                    ? 'GPU acceleration active'
                    : 'Running on CPU — GPU not available to this container'
                }
              />
              <Row
                label="Frames published"
                value={info ? info.frames_published.toLocaleString() : '––'}
                mono
              />
              <Row
                label="Frames encoded"
                value={info ? info.frames_encoded.toLocaleString() : '––'}
                mono
                hint="Lower than published — frames are encoded once and shared between viewers"
              />
            </PanelBody>
          </Panel>
        </section>

        <section>
          <SectionHeading title="Security" />
          <Panel>
            <PanelHeader
              title="Access control"
              icon={<ShieldAlert className="h-3.5 w-3.5" />}
              rail="shadow-rail-warn"
            />
            <PanelBody>
              <div className="flex items-start gap-2.5">
                <StatusLed tone="bg-warn" className="mt-1" />
                <div>
                  <p className="text-xs font-medium text-ink">Authentication not enabled</p>
                  <p className="mt-1 text-2xs leading-relaxed text-ink-faint">
                    Every API endpoint is currently open. Place the stack behind an authenticating
                    reverse proxy, or add authentication to the API, before exposing it beyond a
                    trusted network.
                  </p>
                  <Badge className="mt-2 border-warn/30 bg-warn/10 text-warn">
                    <Sliders className="h-3 w-3" />
                    Action required
                  </Badge>
                </div>
              </div>
            </PanelBody>
          </Panel>
        </section>
      </div>
    </AppLayout>
  );
}

/** One read-only configuration row. */
function Row({
  label,
  value,
  hint,
  mono = false,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  mono?: boolean;
  tone?: 'safe' | 'warn' | 'crit' | 'info' | 'neutral';
}) {
  const tones = {
    safe: 'text-safe',
    warn: 'text-warn',
    crit: 'text-crit',
    info: 'text-info',
    neutral: 'text-ink-dim',
  } as const;

  return (
    <div className="flex items-start justify-between gap-4 border-b border-edge-soft px-3 py-2 last:border-b-0">
      <div className="min-w-0">
        <dt className="text-xs capitalize text-ink-dim">{label}</dt>
        {hint ? <p className="mt-0.5 text-2xs text-ink-ghost">{hint}</p> : null}
      </div>
      <dd
        className={cn(
          'shrink-0 text-right text-xs',
          mono && 'font-mono tabular',
          tone ? tones[tone] : 'text-ink',
        )}
        title={value}
      >
        {value.length > 42 ? `…${value.slice(-40)}` : value}
      </dd>
    </div>
  );
}
