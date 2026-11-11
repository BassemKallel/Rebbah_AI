import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sun, Moon, Search, Bell, ChevronDown, LogOut, Building2 } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';

const TopBar: React.FC = () => {
  const { username, companyName, logout } = useAuth();
  const navigate = useNavigate();

  const [isDarkMode, setIsDarkMode] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Initials from username
  const initials = username ? username.slice(0, 2).toUpperCase() : 'TK';

  const handleLogout = () => {
    setDropdownOpen(false);
    logout();
    navigate('/login');
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <header className="h-16 bg-white/80 backdrop-blur-md border-b border-gray-100 flex items-center justify-between px-6 sm:px-10 flex-shrink-0 z-20 gap-4 shadow-sm">

      {/* Left spacer since branding is now in Sidebar */}
      <div className="flex-1" />

      {/* Right — Actions */}
      <div className="flex items-center gap-1 sm:gap-3 flex-shrink-0">

        {/* Theme toggle */}
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

        {/* ── User profile dropdown ── */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-xl hover:bg-gray-100 transition-colors group"
            aria-label="Menu utilisateur"
          >
            {/* Avatar initials */}
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#0f6885] to-[#0d8fa9] flex items-center justify-center flex-shrink-0 ring-2 ring-gray-100">
              <span className="text-[11px] font-extrabold text-white">{initials}</span>
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-[12px] font-bold text-gray-800 leading-tight">{username || 'Utilisateur'}</p>
              <p className="text-[10px] text-gray-400 leading-tight">{companyName || 'Rebbah AI'}</p>
            </div>
            <ChevronDown
              className={`hidden sm:block w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Dropdown panel */}
          {dropdownOpen && (
            <div className="absolute right-0 top-[calc(100%+8px)] w-56 bg-white border border-gray-100 rounded-2xl shadow-lg overflow-hidden z-50 animate-fade-in">

              {/* User info header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0f6885] to-[#0d8fa9] flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-extrabold text-white">{initials}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-[13px] font-bold text-gray-800 truncate">{username || 'Utilisateur'}</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <Building2 className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      <p className="text-[11px] text-gray-400 truncate">{companyName || 'Rebbah AI'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Menu items */}
              <div className="py-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-semibold text-red-500 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4 flex-shrink-0" />
                  Se déconnecter
                </button>
              </div>
            </div>
          )}
        </div>

      </div>
    </header>
  );
};

export default TopBar;
