import { Navigate, Route, Routes } from 'react-router-dom';
import { DashboardPage } from '@/pages/DashboardPage';
import { LiveMonitoringPage } from '@/pages/LiveMonitoringPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { ViolationsPage } from '@/pages/ViolationsPage';
import { TracksPage } from '@/pages/TracksPage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { SystemHealthPage } from '@/pages/SystemHealthPage';
import { SettingsPage } from '@/pages/SettingsPage';

/** Route table for the dashboard. */
export function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/live" element={<LiveMonitoringPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/violations" element={<ViolationsPage />} />
      <Route path="/tracks" element={<TracksPage />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="/system" element={<SystemHealthPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
