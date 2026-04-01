import React, { useState } from 'react';
import { Sun, Moon, Search, Bell, ChevronDown } from 'lucide-react';

const TopBar = () => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  return (
    <header className="h-14 bg-white border-b border-gray-100 flex items-center justify-between px-6 flex-shrink-0 z-20">

      {/* Left — Page breadcrumb placeholder */}
      <div className="flex-1" />

      {/* Right — Actions */}
      <div className="flex items-center gap-3">

        {/* Theme toggle */}
        <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setIsDarkMode(false)}
            className={`p-1.5 rounded-md transition-colors ${!isDarkMode ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:text-gray-600'}`}
          >
            <Sun className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsDarkMode(true)}
            className={`p-1.5 rounded-md transition-colors ${isDarkMode ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:text-gray-600'}`}
          >
            <Moon className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Search */}
        <button className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
          <Search className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <button className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#0f6885] rounded-full" />
        </button>

        {/* Separator */}
        <div className="w-px h-6 bg-gray-200" />

        {/* User profile */}
        <button className="flex items-center gap-2.5 pl-1 pr-2 py-1 rounded-xl hover:bg-gray-100 transition-colors group">
          <img
            src="https://i.pravatar.cc/150?img=47"
            alt="User"
            className="w-7 h-7 rounded-full object-cover ring-2 ring-gray-100 flex-shrink-0"
          />
          <div className="text-left hidden sm:block">
            <p className="text-[12px] font-bold text-gray-800 leading-tight">Admin</p>
            <p className="text-[10px] text-gray-400">admin@tiktak.ai</p>
          </div>
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-colors" />
        </button>

      </div>
    </header>
  );
};

export default TopBar;
