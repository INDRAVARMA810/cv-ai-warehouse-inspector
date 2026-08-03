import { Navigate, Route, Routes } from 'react-router-dom';
import { DashboardPage } from '@/pages/DashboardPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { ViolationsPage } from '@/pages/ViolationsPage';
import { TracksPage } from '@/pages/TracksPage';
import { SystemHealthPage } from '@/pages/SystemHealthPage';

/** Route table for the dashboard. */
export function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/alerts" element={<AlertsPage />} />
      <Route path="/violations" element={<ViolationsPage />} />
      <Route path="/tracks" element={<TracksPage />} />
      <Route path="/system" element={<SystemHealthPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
