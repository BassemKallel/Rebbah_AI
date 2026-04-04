import React, { useState, useCallback } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

interface MainLayoutProps {
  secondarySidebar?: React.ReactNode;
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ secondarySidebar, children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-white text-gray-800 font-sans">

      {/* ── Mobile backdrop ── */}
      {sidebarOpen && (
        <div
          className="drawer-backdrop md:hidden"
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* ── Primary Sidebar ── */}
      <Sidebar open={sidebarOpen} onClose={closeSidebar} />

      {/* ── Secondary Sidebar — hidden on mobile, visible md+ ── */}
      {secondarySidebar && (
        <div className="
          hidden md:flex md:w-[300px] lg:w-[340px]
          border-r border-gray-100 flex-shrink-0 bg-white flex-col h-full
        ">
          {secondarySidebar}
        </div>
      )}

      {/* ── Main Content Area ── */}
      <div className="flex flex-col flex-1 min-w-0 h-full bg-white relative">
        <TopBar onToggleSidebar={toggleSidebar} />
        <div className="flex-1 min-h-0 relative overflow-y-auto scrollbar-thin">
          {children}
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
