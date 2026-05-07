import React from 'react';
import { Outlet } from 'react-router-dom';
import AdminSidebar from '../../components/layout/AdminSidebar';

export default function AdminMLOpsLayout() {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  return (
    <div className="flex h-screen bg-[#f8fafc] overflow-hidden text-gray-900 font-sans safe-top safe-bottom">
      <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative">
        <main className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin pb-safe relative">
          {/* Header Mobile Only */}
          <div className="md:hidden flex items-center justify-between p-4 bg-white border-b border-gray-100 shadow-sm sticky top-0 z-20">
             <button
                onClick={() => setSidebarOpen(true)}
                className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100"
              >
                <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
             </button>
             <span className="font-semibold text-sm">MLOps Admin</span>
             <div className="w-10"></div>
          </div>
          
          {/* Outlet is where the nested routes will be rendered */}
          <div className="max-w-[1600px] mx-auto p-4 md:p-6 lg:p-8 animate-fade-in-up">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/30 backdrop-blur-sm z-40 animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
