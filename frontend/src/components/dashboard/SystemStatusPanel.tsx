import { Activity, CheckCircle2, XCircle } from 'lucide-react';
import type { Health } from '@/types';
import { cn } from '@/utils/cn';
import { ListSkeleton, Panel, PanelHeader } from '@/components/ui';

interface SystemStatusPanelProps {
  health: Health | undefined;
  isLoading: boolean;
  isError: boolean;
}

/**
 * Per-component platform health.
 *
 * Reports each dependency separately rather than collapsing everything
 * to one light, because "degraded" is only actionable if the operator
 * can see which part is degraded.
 */
export function SystemStatusPanel({ health, isLoading, isError }: SystemStatusPanelProps) {
  const overall = isError
    ? { label: 'Unreachable', tone: 'border-red-500/30 bg-red-500/10 text-red-300' }
    : health?.status === 'ok'
      ? { label: 'Operational', tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' }
      : health?.status === 'degraded'
        ? { label: 'Degraded', tone: 'border-amber-500/30 bg-amber-500/10 text-amber-300' }
        : { label: 'Checking', tone: 'border-surface-600 bg-surface-700/40 text-content-muted' };

  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader
        title="System Status"
        description={health ? `${health.application} v${health.version}` : 'Platform components'}
        icon={<Activity className="h-4 w-4" />}
        actions={
          <span
            className={cn(
              'rounded-md border px-2 py-1 text-[11px] font-medium',
              overall.tone,
            )}
          >
            {overall.label}
          </span>
        }
      />

      {isLoading ? (
        <ListSkeleton rows={2} />
      ) : isError ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 py-8 text-center">
          <XCircle className="h-6 w-6 text-red-300" />
          <p className="text-sm font-medium text-content-primary">API unreachable</p>
          <p className="text-xs text-content-muted">
            The dashboard cannot contact the platform to read component health.
          </p>
        </div>
      ) : (
        <ul className="flex-1 divide-y divide-surface-700/50">
          {(health?.components ?? []).map((component) => (
            <li
              key={component.name}
              className="flex items-center gap-3 px-5 py-3.5"
            >
              {component.healthy ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              ) : (
                <XCircle className="h-4 w-4 shrink-0 text-red-400" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium capitalize text-content-primary">
                  {component.name}
                </p>
                {component.detail ? (
                  <p className="truncate text-xs text-content-muted">{component.detail}</p>
                ) : null}
              </div>
              <span
                className={cn(
                  'shrink-0 text-[11px] font-medium',
                  component.healthy ? 'text-emerald-300' : 'text-red-300',
                )}
              >
                {component.healthy ? 'Healthy' : 'Down'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
