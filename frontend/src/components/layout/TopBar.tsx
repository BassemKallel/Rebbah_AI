import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Bell, Menu, LogOut, User, ChevronDown, Building2 } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';
import { useNavigate } from 'react-router-dom';

interface TopBarProps {
  onToggleSidebar: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar }) => {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { username, companyName, logout } = useAuth();
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    setIsDropdownOpen(false);
    logout();
    navigate('/login');
  };

  // Generate initials avatar from username
  const initials = username
    ? username.slice(0, 2).toUpperCase()
    : 'TK';

  return (
    <header className="h-14 bg-white border-b border-gray-100 flex items-center justify-between px-3 sm:px-6 flex-shrink-0 z-20 gap-2">

      {/* Left — Hamburger (mobile only) */}
      <div className="flex items-center gap-2 flex-shrink-0">
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

        {/* User profile with dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            id="profile-btn"
            onClick={() => setIsDropdownOpen((v) => !v)}
            className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-xl hover:bg-gray-100 transition-colors group"
            aria-haspopup="true"
            aria-expanded={isDropdownOpen}
          >
            {/* Avatar initials */}
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#0f6885] to-[#0d8fa9] flex items-center justify-center flex-shrink-0 ring-2 ring-gray-100">
              <span className="text-[10px] font-bold text-white">{initials}</span>
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-[12px] font-bold text-gray-800 leading-tight">{username || 'Utilisateur'}</p>
              <p className="text-[10px] text-gray-400">{companyName || 'TikTak AI'}</p>
            </div>
            <ChevronDown
              className={`hidden sm:block w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Dropdown menu */}
          {isDropdownOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-56 bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden z-50"
              style={{ boxShadow: '0 8px 30px rgba(0,0,0,0.10)' }}
            >
              {/* User info header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-[#f0f9fc] to-white">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#0f6885] to-[#0d8fa9] flex items-center justify-center flex-shrink-0">
                    <span className="text-[13px] font-bold text-white">{initials}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-[13px] font-bold text-gray-800 truncate">{username || 'Utilisateur'}</p>
                    <p className="text-[11px] text-gray-400 truncate">{companyName || 'TikTak AI'}</p>
                  </div>
                </div>
              </div>

              {/* Menu items */}
              <div className="py-1.5">
                <button
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-[13px] text-gray-600 hover:bg-gray-50 hover:text-[#0f6885] transition-colors group"
                  onClick={() => { setIsDropdownOpen(false); navigate('/profile'); }}
                >
                  <User className="w-4 h-4 text-gray-400 group-hover:text-[#0f6885]" />
                  Mon profil
                </button>

                <button
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-[13px] text-gray-600 hover:bg-gray-50 hover:text-[#0f6885] transition-colors group"
                  onClick={() => setIsDropdownOpen(false)}
                >
                  <Building2 className="w-4 h-4 text-gray-400 group-hover:text-[#0f6885]" />
                  Ma boutique
                </button>
              </div>

              {/* Divider + Logout */}
              <div className="border-t border-gray-100 py-1.5">
                <button
                  id="logout-btn"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-[13px] font-semibold text-red-500 hover:bg-red-50 transition-colors group"
                >
                  <LogOut className="w-4 h-4" />
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
