import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Home, MessageCircle, Users, Settings, X } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', end: true, icon: Home, label: 'Accueil' },
  { to: '/messenger', end: false, icon: MessageCircle, label: 'Messenger' },
  { to: '/leads', end: false, icon: Users, label: 'Leads' },
];

interface SidebarProps {
  /** Controlled by MainLayout — only matters on mobile (<md) */
  open: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  // Desktop collapse state (md+): persisted in localStorage
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('sidebar_collapsed') === 'true'
  );

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem('sidebar_collapsed', String(next));
      return next;
    });
  };

  // Close mobile drawer on route change
  useEffect(() => {
    const handler = () => onClose();
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, [onClose]);

  /* ─────────────────────────────────────────────────────────────
     On mobile (<md): the sidebar is a FIXED drawer overlay.
     On md+:          the sidebar is inline, user-controlled width.
  ───────────────────────────────────────────────────────────── */

  const navContent = (isMobile: boolean) => (
    <>
      {/* ── Brand header ── */}
      <div className="flex items-center gap-3 px-3 py-4 border-b border-gray-100 flex-shrink-0">
        <button
          onClick={isMobile ? onClose : toggle}
          className="w-9 h-9 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center hover:opacity-80 transition-opacity cursor-pointer"
          aria-label={isMobile ? 'Fermer le menu' : 'Toggle sidebar'}
        >
          {isMobile ? (
            <X className="w-5 h-5 text-gray-600" />
          ) : (
            <img
              src="/logo.png"
              alt="Logo"
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
        </button>

        {/* Brand text: always visible on mobile, controlled by collapsed on md+ */}
        {(isMobile || !collapsed) && (
          <div className="flex-1 min-w-0">
            <p className="text-gray-900 font-bold text-sm leading-tight tracking-tight truncate">
              Tiktak <span className="text-[#0f6885]">AI</span>
            </p>
            <span className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">
              Pro Dashboard
            </span>
          </div>
        )}
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 py-3 px-2 overflow-hidden space-y-0.5">
        {(!collapsed || isMobile) && (
          <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest px-3 mb-2">
            Navigation
          </p>
        )}

        {NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={isMobile ? onClose : undefined}
            title={collapsed && !isMobile ? label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 group relative
               ${isActive
                ? 'bg-[#eef6f9] text-[#0f6885]'
                : 'text-gray-500 hover:bg-[#eef6f9] hover:text-[#0f6885]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#0f6885] rounded-r-full" />
                )}
                <Icon className="w-5 h-5 flex-shrink-0" />
                {(!collapsed || isMobile) && (
                  <span className="text-[13px] font-semibold whitespace-nowrap">{label}</span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── Bottom: Settings ── */}
      <div className="px-2 py-3 border-t border-gray-100 flex-shrink-0">
        <NavLink
          to="/settings"
          onClick={isMobile ? onClose : undefined}
          title={collapsed && !isMobile ? 'Paramètres' : undefined}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 relative
             ${isActive
              ? 'bg-[#eef6f9] text-[#0f6885]'
              : 'text-gray-500 hover:bg-[#eef6f9] hover:text-[#0f6885]'
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#0f6885] rounded-r-full" />
              )}
              <Settings className="w-5 h-5 flex-shrink-0" />
              {(!collapsed || isMobile) && (
                <span className="text-[13px] font-semibold">Paramètres</span>
              )}
            </>
          )}
        </NavLink>
      </div>
    </>
  );

  return (
    <>
      {/* ──────────────────────────────────────────────────────────
          MOBILE DRAWER  (fixed overlay, <md)
      ────────────────────────────────────────────────────────── */}
      <div
        className={`
          md:hidden
          fixed inset-y-0 left-0 z-50
          flex flex-col
          bg-white border-r border-gray-100 shadow-panel
          w-[264px] h-full
          transition-transform duration-200 ease-in-out
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
        aria-label="Menu de navigation"
      >
        {navContent(true)}
      </div>

      {/* ──────────────────────────────────────────────────────────
          DESKTOP INLINE SIDEBAR  (md+)
      ────────────────────────────────────────────────────────── */}
      <div
        style={{
          width: collapsed ? '68px' : '264px',
          transition: 'width 0.2s ease',
          background: '#ffffff',
          borderRight: '1px solid #e5e7eb',
          boxShadow: '2px 0 8px rgba(0,0,0,0.04)',
        }}
        className="hidden md:flex relative flex-shrink-0 h-full flex-col z-30 select-none overflow-hidden"
      >
        {/* Logo button (replaces X on desktop) */}
        <div className="flex items-center gap-3 px-3 py-4 border-b border-gray-100 flex-shrink-0">
          <button
            onClick={toggle}
            className="w-9 h-9 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center hover:opacity-80 transition-opacity cursor-pointer"
            aria-label="Toggle sidebar"
          >
            <img
              src="/logo.png"
              alt="Logo"
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </button>

          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-gray-900 font-bold text-sm leading-tight tracking-tight truncate">
                Tiktak <span className="text-[#0f6885]">AI</span>
              </p>
              <span className="text-[10px] text-gray-400 font-medium uppercase tracking-widest">
                Pro Dashboard
              </span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 overflow-hidden space-y-0.5">
          {!collapsed && (
            <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest px-3 mb-2">
              Navigation
            </p>
          )}
          {NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 group relative
                 ${isActive
                  ? 'bg-[#eef6f9] text-[#0f6885]'
                  : 'text-gray-500 hover:bg-[#eef6f9] hover:text-[#0f6885]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#0f6885] rounded-r-full" />
                  )}
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!collapsed && (
                    <span className="text-[13px] font-semibold whitespace-nowrap">{label}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Settings */}
        <div className="px-2 py-3 border-t border-gray-100 flex-shrink-0">
          <NavLink
            to="/settings"
            title={collapsed ? 'Paramètres' : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 relative
               ${isActive
                ? 'bg-[#eef6f9] text-[#0f6885]'
                : 'text-gray-500 hover:bg-[#eef6f9] hover:text-[#0f6885]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#0f6885] rounded-r-full" />
                )}
                <Settings className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span className="text-[13px] font-semibold">Paramètres</span>}
              </>
            )}
          </NavLink>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
