import React from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

const MainLayout = ({ secondarySidebar, children }) => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white text-gray-800 font-sans">
      {/* Primary Sidebar */}
      <Sidebar />
      
      {/* Secondary Sidebar (e.g. Chat List, Settings Menu) */}
      {secondarySidebar && (
        <div className="w-[340px] border-r border-gray-100 flex-shrink-0 bg-white flex flex-col h-full">
          {secondarySidebar}
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 h-full bg-white relative">
        <TopBar />
        <div className="flex-1 min-h-0 relative overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
