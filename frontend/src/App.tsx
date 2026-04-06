import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './providers/AuthProvider';
import RequireAuth from './components/guards/RequireAuth';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import Inbox from './pages/Inbox/Inbox';
import ClientChat from './pages/ClientChat/ClientChat';
import AgentSettingsLayout from './pages/AgentSettings/AgentSettingsLayout';
import MessengerInbox from './pages/MessengerInbox/MessengerInbox';
import Leads from './pages/Leads/Leads';
import Login from './pages/Login/Login';
import Profile from './pages/Profile/Profile';


function App() {
  return (
    <AuthProvider>
      <Router>
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
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
