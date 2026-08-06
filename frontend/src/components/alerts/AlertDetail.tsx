import { Check, CheckCheck, TrendingUp, X } from 'lucide-react';
import type { Alert } from '@/types';
import { useAcknowledgeAlert, useResolveAlert } from '@/hooks';
import { formatDateTime, formatRelative, humanise, shortId } from '@/utils/format';
import { categoryLabel } from '@/utils/severity';
import { cn } from '@/utils/cn';
import { Button, ErrorState, IconButton, LevelBadge, StatusBadge } from '@/components/ui';

interface AlertDetailProps {
  alert: Alert | null;
  onClose: () => void;
}

/**
 * Slide-over panel showing an alert in full, with operator actions.
 *
 * Acknowledge and resolve are separate, sequential steps: acknowledging
 * records that a human has seen the incident, resolving asserts the
 * hazard is gone. Collapsing them into one button would lose the
 * distinction the audit trail depends on.
 */
export function AlertDetail({ alert, onClose }: AlertDetailProps) {
  const acknowledge = useAcknowledgeAlert();
  const resolve = useResolveAlert();

  const open = alert !== null;
  const mutationError = acknowledge.error ?? resolve.error;
  const isBusy = acknowledge.isPending || resolve.isPending;

  return (
    <>
      <div
        aria-hidden
        onClick={onClose}
        className={cn(
          'fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <aside
        role="dialog"
        aria-label="Alert detail"
        aria-hidden={!open}
        className={cn(
          'fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-edge bg-panel shadow-panel',
          'transition-transform duration-200 ease-out',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {alert ? (
          <>
            <header className="flex items-start justify-between gap-3 border-b border-edge px-5 py-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <LevelBadge level={alert.level} />
                  <StatusBadge status={alert.status} />
                  {alert.was_escalated ? (
                    <span className="inline-flex items-center gap-1 text-[11px] text-warn">
                      <TrendingUp className="h-3 w-3" />
                      from {alert.initial_level}
                    </span>
                  ) : null}
                </div>
                <h2 className="mt-2 text-sm font-semibold leading-snug text-ink">
                  {alert.message}
                </h2>
              </div>
              <IconButton label="Close detail" icon={<X className="h-4 w-4" />} onClick={onClose} />
            </header>

            <div className="flex-1 overflow-y-auto">
              <dl className="divide-y divide-edge-soft">
                <DetailRow label="Alert ID" value={alert.alert_id} mono />
                <DetailRow label="Rule" value={humanise(alert.rule_name.replace(/Rule$/, ''))} />
                <DetailRow label="Category" value={categoryLabel(alert.category)} />
                <DetailRow
                  label="Raised"
                  value={formatDateTime(alert.occurred_at)}
                  hint={formatRelative(alert.occurred_at)}
                />
                <DetailRow label="Observations" value={String(alert.occurrence_count)} mono />
                <DetailRow
                  label="Track"
                  value={alert.track_id !== null ? `#${alert.track_id}` : 'Scene-level'}
                  mono={alert.track_id !== null}
                />
                <DetailRow
                  label="Frame"
                  value={alert.frame_number !== null ? String(alert.frame_number) : '—'}
                  mono
                />
                {alert.acknowledged ? (
                  <DetailRow
                    label="Acknowledged"
                    value={alert.acknowledged_by ?? 'Unattributed'}
                    hint={formatDateTime(alert.acknowledged_at)}
                  />
                ) : null}
                {alert.resolved ? (
                  <DetailRow label="Resolved" value={formatDateTime(alert.resolved_at)} />
                ) : null}
                {alert.bounding_box ? (
                  <DetailRow
                    label="Bounding box"
                    value={`${Math.round(alert.bounding_box.x1)}, ${Math.round(alert.bounding_box.y1)} → ${Math.round(alert.bounding_box.x2)}, ${Math.round(alert.bounding_box.y2)}`}
                    mono
                  />
                ) : null}
              </dl>

              {alert.metadata && Object.keys(alert.metadata).length > 0 ? (
                <section className="border-t border-edge/50 px-5 py-4">
                  <h3 className="text-[11px] font-medium uppercase tracking-wider text-ink-faint">
                    Rule metadata
                  </h3>
                  <pre className="mt-2 overflow-x-auto rounded-lg border border-edge bg-void p-3 font-mono text-[11px] leading-relaxed text-ink-dim">
                    {JSON.stringify(alert.metadata, null, 2)}
                  </pre>
                </section>
              ) : null}
            </div>

            <footer className="space-y-3 border-t border-edge px-5 py-4">
              {mutationError ? (
                <ErrorState error={mutationError} compact />
              ) : null}

              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="flex-1"
                  icon={<Check className="h-4 w-4" />}
                  loading={acknowledge.isPending}
                  disabled={isBusy || alert.status !== 'active'}
                  onClick={() =>
                    acknowledge.mutate({ alertId: alert.alert_id, acknowledgedBy: 'dashboard' })
                  }
                >
                  Acknowledge
                </Button>
                <Button
                  variant="primary"
                  className="flex-1"
                  icon={<CheckCheck className="h-4 w-4" />}
                  loading={resolve.isPending}
                  disabled={isBusy || alert.resolved || alert.status === 'expired'}
                  onClick={() => resolve.mutate({ alertId: alert.alert_id })}
                >
                  Resolve
                </Button>
              </div>

              <p className="text-[11px] leading-relaxed text-ink-faint">
                {alert.status === 'active'
                  ? 'Acknowledge to record that this incident has been seen; resolve once the hazard has cleared.'
                  : alert.resolved || alert.status === 'expired'
                    ? 'This incident is closed. Closed incidents cannot be reopened.'
                    : 'Already acknowledged — resolve once the hazard has cleared.'}
              </p>
            </footer>
          </>
        ) : null}
      </aside>
    </>
  );
}

function DetailRow({
  label,
  value,
  hint,
  mono = false,
}: {
  label: string;
  value: string;
  hint?: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 py-3">
      <dt className="shrink-0 text-xs text-ink-faint">{label}</dt>
      <dd className="min-w-0 text-right">
        <span
          className={cn(
            'block break-words text-xs text-ink',
            mono && 'font-mono',
          )}
          title={value}
        >
          {mono && value.length > 24 ? shortId(value, 24) + '…' : value}
        </span>
        {hint ? <span className="mt-0.5 block text-[11px] text-ink-faint">{hint}</span> : null}
      </dd>
    </div>
  );
}
