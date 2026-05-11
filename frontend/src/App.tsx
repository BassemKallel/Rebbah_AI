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
import Retraining from './pages/AdminMLOps/Retraining/Retraining';
import ManualDatasetView from './pages/AdminMLOps/ManualDataset/ManualDatasetView';


function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <Router>
          <Toaster 
            position="bottom-right" 
            toastOptions={{ 
              duration: 5000, 
              style: { 
                borderRadius: '16px', 
                padding: '16px 24px', 
                color: '#1f2937', 
                fontWeight: 500,
                fontSize: '14px',
                boxShadow: '0 10px 40px -10px rgba(0,0,0,0.12)',
                border: '1px solid #f1f5f9',
                background: '#ffffff'
              },
              success: {
                iconTheme: { primary: '#10b981', secondary: '#ffffff' },
              },
              error: {
                iconTheme: { primary: '#ef4444', secondary: '#ffffff' },
              }
            }} 
          />
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
                <Route path="manual-dataset" element={<ManualDatasetView />} />
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
