import { NavLink } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  LayoutDashboard,
  Radar,
  ShieldAlert,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { IconButton } from '@/components/ui';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: 'Overview',
    icon: LayoutDashboard,
    description: 'Live operational summary',
  },
  { to: '/alerts', label: 'Alerts', icon: AlertTriangle, description: 'Safety incidents' },
  { to: '/violations', label: 'Violations', icon: ShieldAlert, description: 'Rule breaches' },
  { to: '/tracks', label: 'Tracks', icon: Radar, description: 'Detected objects' },
  { to: '/system', label: 'System Health', icon: Activity, description: 'Platform status' },
];

interface SidebarProps {
  /** Whether the drawer is open on small screens. */
  open: boolean;
  onClose: () => void;
  /** Live count of active alerts, badged against the Alerts item. */
  activeAlertCount?: number;
}

/**
 * Primary navigation.
 *
 * Renders as a fixed rail from `lg` upward and as an overlay drawer
 * below it, so the same component serves both without duplicated markup.
 */
export function Sidebar({ open, onClose, activeAlertCount = 0 }: SidebarProps) {
  return (
    <>
      {/* Scrim, mobile only */}
      <div
        onClick={onClose}
        aria-hidden
        className={cn(
          'fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-surface-700/70 bg-surface-900',
          'transition-transform duration-200 ease-out lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center justify-between gap-3 border-b border-surface-700/70 px-5">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-accent/30 bg-accent/10 text-accent">
              <ShieldAlert className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold leading-tight text-content-primary">
                Safety Inspector
              </p>
              <p className="truncate text-[11px] leading-tight text-content-muted">
                Warehouse Operations
              </p>
            </div>
          </div>
          <IconButton
            label="Close navigation"
            icon={<X className="h-4 w-4" />}
            onClick={onClose}
            className="lg:hidden"
          />
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const showBadge = item.to === '/alerts' && activeAlertCount > 0;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors',
                    isActive
                      ? 'border-accent/30 bg-accent/10 text-accent'
                      : 'border-transparent text-content-secondary hover:bg-surface-800 hover:text-content-primary',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className={cn('h-4 w-4 shrink-0', !isActive && 'opacity-70')} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium leading-tight">
                        {item.label}
                      </span>
                      <span className="block truncate text-[11px] leading-tight text-content-muted">
                        {item.description}
                      </span>
                    </span>
                    {showBadge ? (
                      <span className="shrink-0 rounded-md border border-rose-500/40 bg-rose-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold tabular-nums text-rose-300">
                        {activeAlertCount > 99 ? '99+' : activeAlertCount}
                      </span>
                    ) : null}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-surface-700/70 p-4">
          <p className="text-[11px] leading-relaxed text-content-muted">
            AI Warehouse Safety Inspector
            <br />
            <span className="font-mono">YOLO · ByteTrack · FastAPI</span>
          </p>
        </div>
      </aside>
    </>
  );
}
