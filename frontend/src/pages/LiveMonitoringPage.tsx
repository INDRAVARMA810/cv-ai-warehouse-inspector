import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cpu, Gauge, MonitorPlay, Radar, Siren, Users } from 'lucide-react';
import { useAlerts, useStreamStatus, useTracks } from '@/hooks';
import { AppLayout } from '@/components/layout';
import { CameraPanel, SystemStatusPanel } from '@/components/dashboard';
import { AlertFeed } from '@/components/alerts';
import { Panel, PanelHeader, StatCard } from '@/components/ui';
import { workerCount } from '@/utils/stats';
import { formatDuration } from '@/utils/format';

/**
 * Full-bleed monitoring station.
 *
 * The camera dominates the viewport, with only the readings an operator
 * needs while actually watching the floor: live alerts, occupancy and
 * pipeline throughput. Everything analytical is deliberately absent —
 * this is the screen left up on a wall display.
 */
export function LiveMonitoringPage() {
  const navigate = useNavigate();
  const stream = useStreamStatus(5_000);
  const tracks = useTracks({ page: 1, page_size: 100, sort_by: 'first_seen', order: 'desc' });
  const alerts = useAlerts(
    { page: 1, page_size: 12, status: 'active', sort_by: 'occurred_at', order: 'desc' },
    10_000,
  );

  const info = stream.data;
  const workers = useMemo(() => workerCount(tracks.data?.items ?? []), [tracks.data]);

  return (
    <AppLayout
      title="Live Monitoring"
      subtitle="Real-time detection feed"
      onRefresh={() => {
        void stream.refetch();
        void alerts.refetch();
        void tracks.refetch();
      }}
      isRefreshing={stream.isFetching || alerts.isFetching}
      wide
    >
      <div className="grid grid-cols-1 gap-3 2xl:grid-cols-4">
        {/* Feed */}
        <div className="2xl:col-span-3">
          <Panel className="overflow-hidden">
            <PanelHeader
              title="Camera 01 — Main Floor"
              subtitle="Bounding boxes · track IDs · danger zones · violation overlay"
              icon={<MonitorPlay className="h-3.5 w-3.5" />}
            />
            <CameraPanel bare fps={20} />
          </Panel>

          <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Workers On Floor"
              value={workers}
              icon={<Users className="h-3.5 w-3.5" />}
              tone={workers > 0 ? 'info' : 'neutral'}
              hint="Person tracks, last 15 min"
              isLoading={tracks.isLoading}
            />
            <StatCard
              label="Active Alerts"
              value={alerts.data?.meta.total ?? 0}
              icon={<Siren className="h-3.5 w-3.5" />}
              tone={(alerts.data?.meta.total ?? 0) > 0 ? 'crit' : 'safe'}
              hint="Awaiting acknowledgement"
              isLoading={alerts.isLoading}
            />
            <StatCard
              label="Frame Rate"
              value={info?.publish_fps ? info.publish_fps.toFixed(1) : '––'}
              unit="fps"
              icon={<Gauge className="h-3.5 w-3.5" />}
              tone={!info?.publish_fps ? 'neutral' : info.publish_fps >= 10 ? 'safe' : 'warn'}
              hint={info?.viewers ? `${info.viewers} viewer(s)` : 'No viewers'}
              isLoading={stream.isLoading}
            />
            <StatCard
              label="Inference Device"
              value={info?.device?.toUpperCase() ?? '––'}
              icon={<Cpu className="h-3.5 w-3.5" />}
              tone={info?.device === 'cuda' ? 'safe' : info?.device ? 'info' : 'neutral'}
              hint={info?.uptime ? `Up ${formatDuration(info.uptime)}` : 'Stream idle'}
              isLoading={stream.isLoading}
            />
          </div>
        </div>

        {/* Side rail */}
        <div className="flex flex-col gap-3">
          <Panel className="flex flex-col overflow-hidden">
            <PanelHeader
              title="Live Alerts"
              subtitle="Active incidents"
              icon={<Siren className="h-3.5 w-3.5" />}
              rail={(alerts.data?.meta.total ?? 0) > 0 ? 'shadow-rail-crit' : 'shadow-rail-safe'}
            />
            <div className="max-h-[28rem] flex-1 overflow-y-auto">
              <AlertFeed
                alerts={alerts.data?.items ?? []}
                isLoading={alerts.isLoading}
                error={alerts.error}
                onRetry={() => void alerts.refetch()}
                emptyTitle="Floor is clear"
                emptyDescription="No active alerts."
                emptyPositive
                onSelect={(alert) => navigate(`/alerts?focus=${alert.alert_id}`)}
              />
            </div>
          </Panel>

          <SystemStatusPanel />

          <Panel className="overflow-hidden">
            <PanelHeader
              title="Tracked Objects"
              subtitle="Most recent identities"
              icon={<Radar className="h-3.5 w-3.5" />}
            />
            <ul className="max-h-64 overflow-y-auto">
              {(tracks.data?.items ?? []).slice(0, 10).map((track) => (
                <li
                  key={track.id}
                  className="flex items-center gap-2 border-b border-edge-soft px-3 py-1.5 last:border-b-0"
                >
                  <span className="font-mono text-2xs tabular text-info">#{track.track_id}</span>
                  <span className="truncate text-2xs capitalize text-ink-dim">
                    {track.class_name}
                  </span>
                  <span className="ml-auto font-mono text-2xs tabular text-ink-ghost">
                    {track.observation_count}f
                  </span>
                </li>
              ))}
              {(tracks.data?.items.length ?? 0) === 0 && !tracks.isLoading ? (
                <li className="px-3 py-6 text-center text-2xs text-ink-ghost">
                  No tracked objects
                </li>
              ) : null}
            </ul>
          </Panel>
        </div>
      </div>
    </AppLayout>
  );
}
