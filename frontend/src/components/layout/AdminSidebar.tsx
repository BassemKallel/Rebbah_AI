import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { BarChart3, CheckSquare, Download, RefreshCw, X, LogOut } from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';

const ADMIN_NAV_ITEMS = [
  { to: '/admin/mlops', end: true, icon: BarChart3, label: 'Dashboard MLOps' },
  { to: '/admin/review', end: false, icon: CheckSquare, label: 'Révision labels' },
  { to: '/admin/export', end: false, icon: Download, label: 'Export dataset' },
  { to: '/admin/retrain', end: false, icon: RefreshCw, label: 'Réentraînement' },
];

interface AdminSidebarProps {
  /** Controlled by MainLayout — only matters on mobile (<md) */
  open: boolean;
  onClose: () => void;
}

const AdminSidebar: React.FC<AdminSidebarProps> = ({ open, onClose }) => {
  const { logout } = useAuth();
  
  // Desktop collapse state (md+): persisted in localStorage
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('admin_sidebar_collapsed') === 'true'
  );

  const toggle = () => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem('admin_sidebar_collapsed', String(next));
      return next;
    });
  };

  // Close mobile drawer on route change
  useEffect(() => {
    const handler = () => onClose();
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, [onClose]);

  const navLinkClass = (isActive: boolean) =>
    `flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 group relative
     ${isActive
      ? 'bg-[#eef6f9] text-[#0f6885]'
      : 'text-gray-500 hover:bg-[#eef6f9] hover:text-[#0f6885]'
    }`;

  const activeDot = (
    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#0f6885] rounded-r-full" />
  );

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

        {(isMobile || !collapsed) && (
          <div className="flex-1 min-w-0">
            <p className="text-gray-900 font-bold text-sm leading-tight tracking-tight truncate">
              Tiktak <span className="text-[#0f6885]">AI</span>
            </p>
            <span className="text-[10px] bg-red-50 text-red-500 font-bold uppercase tracking-widest px-2 py-0.5 rounded-full inline-block mt-1">
              Admin MLOps
            </span>
          </div>
        )}
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 py-3 px-2 overflow-hidden space-y-0.5">
        {(!collapsed || isMobile) && (
          <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest px-3 mb-2 mt-2">
            Modèles & Data
          </p>
        )}

        {ADMIN_NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={isMobile ? onClose : undefined}
            title={collapsed && !isMobile ? label : undefined}
            className={({ isActive }) => navLinkClass(isActive)}
          >
            {({ isActive }) => (
              <>
                {isActive && activeDot}
                <Icon className="w-5 h-5 flex-shrink-0" />
                {(!collapsed || isMobile) && (
                  <span className="text-[13px] font-semibold whitespace-nowrap">{label}</span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* ── Bottom: Logout ── */}
      <div className="px-2 py-3 border-t border-gray-100 flex-shrink-0">
        <button
          onClick={() => {
            if (isMobile) onClose();
            logout();
          }}
          title={collapsed && !isMobile ? 'Déconnexion' : undefined}
          className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 group relative text-red-500 hover:bg-red-50 hover:text-red-600"
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {(!collapsed || isMobile) && (
            <span className="text-[13px] font-semibold">Déconnexion</span>
          )}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* MOBILE DRAWER */}
      <div
        className={`
          md:hidden fixed inset-y-0 left-0 z-50
          flex flex-col bg-white border-r border-gray-100 shadow-panel
          w-[264px] h-full
          transition-transform duration-200 ease-in-out
          ${open ? 'translate-x-0' : '-translate-x-full'}
        `}
        aria-label="Menu de navigation"
      >
        {navContent(true)}
      </div>

      {/* DESKTOP INLINE SIDEBAR */}
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
        {/* Logo button */}
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
            <div className="flex-1 min-w-0 mt-0.5">
              <p className="text-gray-900 font-bold text-sm leading-tight tracking-tight truncate">
                Tiktak <span className="text-[#0f6885]">AI</span>
              </p>
              <span className="text-[10px] bg-red-50 text-red-500 font-bold uppercase tracking-widest px-2 py-0.5 rounded-full inline-block mt-1">
                Admin MLOps
              </span>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 overflow-hidden space-y-0.5">
          {!collapsed && (
            <p className="text-[10px] font-bold text-gray-300 uppercase tracking-widest px-3 mb-2 mt-2">
              Modèles & Data
            </p>
          )}
          {ADMIN_NAV_ITEMS.map(({ to, end, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              title={collapsed ? label : undefined}
              className={({ isActive }) => navLinkClass(isActive)}
            >
              {({ isActive }) => (
                <>
                  {isActive && activeDot}
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!collapsed && (
                    <span className="text-[13px] font-semibold whitespace-nowrap">{label}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Settings / Logout */}
        <div className="px-2 py-3 border-t border-gray-100 flex-shrink-0">
          <button
            onClick={() => logout()}
            title={collapsed ? 'Déconnexion' : undefined}
            className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-150 group relative text-red-500 hover:bg-red-50 hover:text-red-600 cursor-pointer"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span className="text-[13px] font-semibold">Déconnexion</span>}
          </button>
        </div>
      </div>
    </>
  );
};

export default AdminSidebar;
