import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './providers/AuthProvider';
import { QueryProvider } from './providers/QueryProvider';
import RequireAuth from './components/guards/RequireAuth';
import RequireAdmin from './components/guards/RequireAdmin';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import Inbox from './pages/Inbox/Inbox';
import ClientChat from './pages/ClientChat/ClientChat';
import AgentSettingsLayout from './pages/AgentSettings/AgentSettingsLayout';
import MessengerInbox from './pages/MessengerInbox/MessengerInbox';
import Leads from './pages/Leads/Leads';
import Login from './pages/Login/Login';
import Profile from './pages/Profile/Profile';

import AdminMLOpsLayout from './pages/AdminMLOps/AdminMLOpsLayout';
import MLOpsDashboard from './pages/AdminMLOps/MLOpsDashboard/MLOpsDashboard';
import PredictionReview from './pages/AdminMLOps/PredictionReview/PredictionReview';
import DatasetExport from './pages/AdminMLOps/DatasetExport/DatasetExport';
import Retraining from './pages/AdminMLOps/Retraining/Retraining';


function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <Router>
          <Toaster position="top-right" toastOptions={{ duration: 4000, style: { borderRadius: '12px', padding: '16px', color: '#1f2937', fontWeight: 600 } }} />
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/chat" element={<ClientChat />} />

            {/* Protected routes — require JWT auth */}
            <Route element={<RequireAuth />}>
              <Route path="/settings/*" element={<AgentSettingsLayout />} />
              <Route path="/messenger" element={<MessengerInbox />} />
              <Route
                path="/*"
                element={
                  <MainLayout>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/inbox" element={<Inbox />} />
                      <Route path="/leads" element={<Leads />} />
                      <Route path="/profile" element={<Profile />} />
                    </Routes>
                  </MainLayout>
                }
              />
            </Route>

            {/* Admin routes — require admin role */}
            <Route element={<RequireAdmin />}>
              <Route path="/admin/*" element={<AdminMLOpsLayout />}>
                <Route path="mlops" element={<MLOpsDashboard />} />
                <Route path="review" element={<PredictionReview />} />
                <Route path="export" element={<DatasetExport />} />
                <Route path="retrain" element={<Retraining />} />
              </Route>
            </Route>
          </Routes>
        </Router>
      </AuthProvider>
    </QueryProvider>
  );
}

export default App;
