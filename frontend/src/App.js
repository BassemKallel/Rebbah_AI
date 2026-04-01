import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import Inbox from './pages/Inbox/Inbox';
import ClientChat from './pages/ClientChat/ClientChat';
import AgentSettingsLayout from './pages/AgentSettings/AgentSettingsLayout';
import MessengerInbox from './pages/MessengerInbox/MessengerInbox';
import Leads from './pages/Leads/Leads';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        {/* Client-facing chat page — no sidebar */}
        <Route path="/chat" element={<ClientChat />} />

        {/* Agent Settings route */}
        <Route path="/settings/*" element={<AgentSettingsLayout />} />

        {/* Messenger route — manages its own MainLayout (with secondarySidebar) */}
        <Route path="/messenger" element={<MessengerInbox />} />

        {/* Layout for App sections */}
        <Route
          path="/*"
          element={
            <MainLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/inbox" element={<Inbox />} />
                <Route path="/leads" element={<Leads />} />
              </Routes>
            </MainLayout>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
