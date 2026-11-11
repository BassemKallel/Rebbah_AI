import React from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-gray-50 text-gray-800 font-sans">
      {/* ── Global Sidebar ── */}
      <Sidebar />

      {/* ── Main Content Area ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* We keep TopBar for the user profile dropdown and global actions */}
        <TopBar />
        
        {/* Scrollable Page Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-8 md:p-10 animate-in fade-in duration-300">
          {children}
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
