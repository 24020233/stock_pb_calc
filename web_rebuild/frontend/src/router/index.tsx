import { createBrowserRouter } from 'react-router-dom';
import App from '@/App';
import HomePage from '@/pages/HomePage';
import ReportsPage from '@/pages/ReportsPage';
import ReportDetail from '@/pages/ReportDetail';
import SettingsPage from '@/pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'reports',
        element: <ReportsPage />,
      },
      {
        path: 'reports/:id',
        element: <ReportDetail />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
    ],
  },
]);
