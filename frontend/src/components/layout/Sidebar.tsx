import React from 'react';
import { NavLink } from 'react-router-dom';
import { Settings, Image as ImageIcon, Sparkles } from 'lucide-react';

const Sidebar: React.FC = () => {
  return (
    <div className="w-64 bg-white border-r border-gray-200 h-full flex flex-col py-6 flex-shrink-0 z-20">
      <div className="mb-8 px-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center bg-gray-50 border border-gray-100">
            <img
              src="/logo.png"
              alt="Logo"
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-gray-900 font-extrabold text-base leading-tight tracking-tight truncate">
              REBBAH <span className="text-[#0f6885]">AI</span>
            </p>
            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">
              Agent Builder
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-1.5 flex-1 px-4">
        <h2 className="text-[11px] font-extrabold text-gray-400 uppercase tracking-widest px-3 mb-2">Menu</h2>

        <NavLink
          to="/bot-config"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-200 ${isActive
              ? 'bg-[#0f6885]/10 text-[#0f6885]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <Settings className={`w-4 h-4 ${isActive ? 'opacity-100' : 'opacity-70 text-gray-400'}`} />
              Configuration du Bot
            </>
          )}
        </NavLink>

        <NavLink
          to="/catalogue"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-200 ${isActive
              ? 'bg-[#0f6885]/10 text-[#0f6885]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <ImageIcon className={`w-4 h-4 ${isActive ? 'opacity-100' : 'opacity-70 text-gray-400'}`} />
              Catalogue
            </>
          )}
        </NavLink>
      </div>
    </div>
  );
};

export default Sidebar;
