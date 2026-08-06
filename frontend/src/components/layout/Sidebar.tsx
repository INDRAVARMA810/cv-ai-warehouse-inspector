import { NavLink } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  HardHat,
  LayoutGrid,
  Radar,
  Settings,
  ShieldAlert,
  Siren,
  Video,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/utils/cn';
import { IconButton } from '@/components/ui';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Short code shown in the collapsed rail. */
  code: string;
}

const PRIMARY: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid, code: 'DSH' },
  { to: '/live', label: 'Live Monitoring', icon: Video, code: 'LIV' },
  { to: '/alerts', label: 'Alerts', icon: Siren, code: 'ALT' },
  { to: '/violations', label: 'Violations', icon: ShieldAlert, code: 'VIO' },
  { to: '/tracks', label: 'Tracks', icon: Radar, code: 'TRK' },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, code: 'ANA' },
];

const SECONDARY: NavItem[] = [
  { to: '/system', label: 'System Health', icon: Activity, code: 'SYS' },
  { to: '/settings', label: 'Settings', icon: Settings, code: 'CFG' },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  /** Live count badged against Alerts. */
  activeAlerts?: number;
  /** Live count badged against Violations. */
  openViolations?: number;
}

/**
 * Primary navigation rail.
 *
 * Fixed from `lg` upward, an overlay drawer below it — one component
 * serving both so the two can never drift. Counts are badged inline
 * because an operator needs to know something demands attention before
 * deciding to navigate to it.
 */
export function Sidebar({ open, onClose, activeAlerts = 0, openViolations = 0 }: SidebarProps) {
  const badgeFor = (to: string): number | undefined => {
    if (to === '/alerts' && activeAlerts > 0) return activeAlerts;
    if (to === '/violations' && openViolations > 0) return openViolations;
    return undefined;
  };

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden
        className={cn(
          'fixed inset-0 z-30 bg-black/70 transition-opacity duration-200 lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-edge bg-panel',
          'transition-transform duration-200 ease-instrument lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Brand */}
        <div className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-edge px-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-control border border-edge-strong bg-panel-inset text-info">
              <HardHat className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold leading-tight text-ink">
                Safety Inspector
              </p>
              <p className="truncate font-mono text-2xs leading-tight text-ink-ghost">
                WAREHOUSE OPS
              </p>
            </div>
          </div>
          <IconButton
            size="sm"
            label="Close navigation"
            icon={<X className="h-3.5 w-3.5" />}
            onClick={onClose}
            className="lg:hidden"
          />
        </div>

        <nav className="flex-1 overflow-y-auto p-2">
          <p className="eyebrow px-2 pb-1.5 pt-1">Operations</p>
          <ul className="space-y-0.5">
            {PRIMARY.map((item) => (
              <NavRow key={item.to} item={item} badge={badgeFor(item.to)} onNavigate={onClose} />
            ))}
          </ul>

          <p className="eyebrow px-2 pb-1.5 pt-4">Platform</p>
          <ul className="space-y-0.5">
            {SECONDARY.map((item) => (
              <NavRow key={item.to} item={item} onNavigate={onClose} />
            ))}
          </ul>
        </nav>

        {/* Build stamp */}
        <div className="shrink-0 border-t border-edge px-3.5 py-2.5">
          <p className="font-mono text-2xs leading-relaxed text-ink-ghost">
            YOLOv8 · ByteTrack
            <br />
            <span className="text-ink-faint">v1.0.0</span> · FastAPI
          </p>
        </div>
      </aside>
    </>
  );
}

/** One navigation row with an active rail and optional count badge. */
function NavRow({
  item,
  badge,
  onNavigate,
}: {
  item: NavItem;
  badge?: number;
  onNavigate: () => void;
}) {
  const Icon = item.icon;

  return (
    <li>
      <NavLink
        to={item.to}
        end={item.to === '/'}
        onClick={onNavigate}
        className={({ isActive }) =>
          cn(
            'group relative flex items-center gap-2.5 rounded-control px-2 py-1.5 transition-colors duration-150',
            isActive
              ? 'bg-info/10 text-info shadow-rail-info'
              : 'text-ink-faint hover:bg-edge-soft hover:text-ink-dim',
          )
        }
      >
        {({ isActive }) => (
          <>
            <Icon className={cn('h-4 w-4 shrink-0', !isActive && 'opacity-70')} />
            <span className="min-w-0 flex-1 truncate text-xs font-medium">{item.label}</span>
            {badge !== undefined ? (
              <span className="shrink-0 rounded-control border border-crit/40 bg-crit/15 px-1 font-mono text-2xs tabular font-semibold text-crit">
                {badge > 99 ? '99+' : badge}
              </span>
            ) : (
              <span className="shrink-0 font-mono text-2xs text-ink-ghost opacity-0 transition-opacity group-hover:opacity-100">
                {item.code}
              </span>
            )}
          </>
        )}
      </NavLink>
    </li>
  );
}
