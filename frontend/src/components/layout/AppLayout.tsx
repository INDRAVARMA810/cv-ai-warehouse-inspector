import { useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useAlerts, useViolations } from '@/hooks';
import { cn } from '@/utils/cn';

interface AppLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  /** Removes the content max-width, for full-bleed screens like Live. */
  wide?: boolean;
}

/**
 * Application shell: fixed rail, sticky instrument bar, scrolling content.
 *
 * Owns only chrome and navigation state. Pages supply their own title
 * and refresh handler, so the shell never needs to know what they show.
 */
export function AppLayout({
  title,
  subtitle,
  children,
  onRefresh,
  isRefreshing,
  wide = false,
}: AppLayoutProps) {
  const [navOpen, setNavOpen] = useState(false);

  // Counts only — `page_size: 1` lets the server do the counting and
  // returns just `meta.total`, so the sidebar badges cost almost nothing.
  const { data: activeAlerts } = useAlerts({ page: 1, page_size: 1, status: 'active' }, 30_000);
  const { data: violations } = useViolations({ page: 1, page_size: 1 });

  return (
    <div className="min-h-screen bg-void text-ink">
      <Sidebar
        open={navOpen}
        onClose={() => setNavOpen(false)}
        activeAlerts={activeAlerts?.meta.total ?? 0}
        openViolations={violations?.meta.total ?? 0}
      />

      <div className="lg:pl-60">
        <TopBar
          title={title}
          subtitle={subtitle}
          onOpenNav={() => setNavOpen(true)}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
        />
        <main
          className={cn(
            'w-full animate-rise-in p-3 sm:p-4',
            !wide && 'mx-auto max-w-[1800px]',
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
