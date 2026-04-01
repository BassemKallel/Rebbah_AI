import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Bell, Search, ChevronDown, Settings, LogOut, User } from 'lucide-react';

const ROUTE_TITLES = {
  '/':             { title: 'Tableau de bord',  sub: 'Vue globale de l\'activité du bot' },
  '/messages':     { title: 'Messages',          sub: 'Conversations clients en temps réel' },
  '/inbox':        { title: 'Inbox',             sub: 'File d\'attente des agents' },
  '/leads':        { title: 'Leads',             sub: 'Prospects et clients détectés' },
  '/notifications':{ title: 'Notifications',     sub: 'Alertes et événements récents' },
};

const NOTIFICATIONS = [
  { id: 1, icon: '🛒', text: 'Nouvelle commande de Alex', time: '3 min', read: false },
  { id: 2, icon: '⚠️', text: 'Fallback activé — Youssef', time: '14 min', read: false },
  { id: 3, icon: '✅', text: 'Commande #1042 confirmée',   time: '21 min', read: true },
];

const Navbar = () => {
  const { pathname } = useLocation();
  const page = ROUTE_TITLES[pathname] || { title: 'Admin', sub: '' };
  const unread = NOTIFICATIONS.filter((n) => !n.read).length;

  const [showNotifs, setShowNotifs] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-20 flex-shrink-0 z-20 relative">

      {/* Left — Page title */}
      <div>
        <h1 className="text-base font-bold text-gray-800 leading-tight">{page.title}</h1>
        {page.sub && <p className="text-xs text-gray-400">{page.sub}</p>}
      </div>

      {/* Center — Search */}
      <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 w-72 mx-8">
        <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <input
          type="text"
          placeholder="Rechercher..."
          className="bg-transparent border-0 focus:outline-none text-sm text-gray-700 placeholder-gray-400 w-full"
        />
      </div>

      {/* Right — Actions */}
      <div className="flex items-center gap-3">

        {/* Shop badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#eef6f9] rounded-xl">
          <div className="w-5 h-5 rounded-full bg-[#0f6885] flex items-center justify-center">
            <span className="text-[9px] font-bold text-white">IS</span>
          </div>
          <span className="text-xs font-semibold text-[#0f6885]">Iconic Store</span>
        </div>

        {/* Bell */}
        <div className="relative">
          <button
            onClick={() => { setShowNotifs((v) => !v); setShowProfile(false); }}
            className="relative p-2 text-gray-400 hover:text-[#0f6885] hover:bg-[#eef6f9] rounded-xl transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unread > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </button>

          {showNotifs && (
            <div className="absolute right-0 top-12 w-80 bg-white rounded-2xl shadow-xl border border-gray-100 z-50 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-bold text-gray-800">Notifications</p>
                {unread > 0 && (
                  <span className="text-[10px] bg-red-100 text-red-600 font-bold rounded-full px-2 py-0.5">{unread} nouvelles</span>
                )}
              </div>
              <div className="divide-y divide-gray-50 max-h-64 overflow-y-auto">
                {NOTIFICATIONS.map((n) => (
                  <div key={n.id} className={`flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors ${!n.read ? 'bg-blue-50/50' : ''}`}>
                    <span className="text-xl flex-shrink-0">{n.icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!n.read ? 'font-semibold text-gray-800' : 'text-gray-600'}`}>{n.text}</p>
                      <p className="text-xs text-gray-400 mt-0.5">Il y a {n.time}</p>
                    </div>
                    {!n.read && <span className="w-2 h-2 bg-[#0f6885] rounded-full flex-shrink-0 mt-1.5" />}
                  </div>
                ))}
              </div>
              <div className="px-4 py-2.5 border-t border-gray-100">
                <button className="w-full text-xs text-[#0f6885] font-semibold hover:underline">
                  Voir tout
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Profile */}
        <div className="relative">
          <button
            onClick={() => { setShowProfile((v) => !v); setShowNotifs(false); }}
            className="flex items-center gap-2 pl-1 pr-2 py-1 hover:bg-gray-50 rounded-xl transition-colors"
          >
            <img
              src="https://i.pravatar.cc/150?img=3"
              alt="Profile"
              className="w-8 h-8 rounded-full object-cover border-2 border-gray-200"
            />
            <div className="text-left hidden sm:block">
              <p className="text-xs font-semibold text-gray-800 leading-tight">Admin</p>
              <p className="text-[11px] text-gray-400">Super Admin</p>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          </button>

          {showProfile && (
            <div className="absolute right-0 top-12 w-48 bg-white rounded-2xl shadow-xl border border-gray-100 z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-semibold text-gray-800">Admin</p>
                <p className="text-xs text-gray-400">admin@tiktak.ai</p>
              </div>
              <div className="py-1">
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
                  <User className="w-4 h-4 text-gray-400" /> Profil
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
                  <Settings className="w-4 h-4 text-gray-400" /> Paramètres
                </button>
                <button className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors">
                  <LogOut className="w-4 h-4" /> Déconnexion
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
