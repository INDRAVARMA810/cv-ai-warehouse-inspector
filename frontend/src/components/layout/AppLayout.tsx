import { useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { useAlerts } from '@/hooks';

interface AppLayoutProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

/**
 * Application shell: fixed sidebar, sticky top bar, scrolling content.
 *
 * Owns only chrome and navigation state. Pages supply their own title
 * and refresh handler so the shell never needs to know what they show.
 */
export function AppLayout({
  title,
  subtitle,
  children,
  onRefresh,
  isRefreshing,
}: AppLayoutProps) {
  const [navOpen, setNavOpen] = useState(false);

  // A lightweight poll purely for the sidebar badge; `page_size: 1`
  // means the server does the counting and only `meta.total` matters.
  const { data: activeAlerts } = useAlerts(
    { page: 1, page_size: 1, status: 'active' },
    30_000,
  );

  return (
    <div className="min-h-screen bg-surface-950 text-content-primary">
      <Sidebar
        open={navOpen}
        onClose={() => setNavOpen(false)}
        activeAlertCount={activeAlerts?.meta.total ?? 0}
      />

      <div className="lg:pl-64">
        <TopBar
          title={title}
          subtitle={subtitle}
          onOpenNav={() => setNavOpen(true)}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
        />
        <main className="mx-auto w-full max-w-[1600px] animate-fade-in p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
