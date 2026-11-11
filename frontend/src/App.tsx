import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './providers/AuthProvider';
import RequireAuth from './components/guards/RequireAuth';
import MainLayout from './components/layout/MainLayout';
import BotConfiguration from './pages/AgentDashboard/BotConfiguration';
import ProductSync from './pages/AgentDashboard/ProductSync';
import Login from './pages/Login/Login';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />

          {/* Protected routes — require JWT auth */}
          <Route element={<RequireAuth />}>
            <Route
              path="/*"
              element={
                <MainLayout>
                  <Routes>
                    <Route path="/bot-config" element={<BotConfiguration />} />
                    <Route path="/catalogue" element={<ProductSync />} />
                    <Route path="*" element={<Navigate to="/bot-config" replace />} />
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
