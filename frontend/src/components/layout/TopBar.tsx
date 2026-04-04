import React, { useState } from 'react';
import { Sun, Moon, Search, Bell, ChevronDown, Menu } from 'lucide-react';

interface TopBarProps {
  onToggleSidebar: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar }) => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  return (
    <header className="h-14 bg-white border-b border-gray-100 flex items-center justify-between px-3 sm:px-6 flex-shrink-0 z-20 gap-2">

      {/* Left — Hamburger (mobile only) + breadcrumb placeholder */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Hamburger — visible only on mobile (<md) */}
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors"
          aria-label="Ouvrir le menu"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right — Actions */}
      <div className="flex items-center gap-1 sm:gap-3 flex-shrink-0">

        {/* Theme toggle — hidden on very small screens */}
        <div className="hidden xs:flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setIsDarkMode(false)}
            className={`p-1.5 rounded-md transition-colors ${!isDarkMode ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:text-gray-600'}`}
            aria-label="Mode clair"
          >
            <Sun className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsDarkMode(true)}
            className={`p-1.5 rounded-md transition-colors ${isDarkMode ? 'bg-white shadow-sm text-gray-700' : 'text-gray-400 hover:text-gray-600'}`}
            aria-label="Mode sombre"
          >
            <Moon className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Search */}
        <button
          className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Rechercher"
        >
          <Search className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <button
          className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#0f6885] rounded-full" />
        </button>

        {/* Separator */}
        <div className="hidden sm:block w-px h-6 bg-gray-200" />

        {/* User profile */}
        <button className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-xl hover:bg-gray-100 transition-colors group">
          <img
            src="https://i.pravatar.cc/150?img=47"
            alt="User"
            className="w-7 h-7 rounded-full object-cover ring-2 ring-gray-100 flex-shrink-0"
          />
          <div className="text-left hidden sm:block">
            <p className="text-[12px] font-bold text-gray-800 leading-tight">Admin</p>
            <p className="text-[10px] text-gray-400">admin@tiktak.ai</p>
          </div>
          <ChevronDown className="hidden sm:block w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-colors" />
        </button>

      </div>
    </header>
  );
};

export default TopBar;
