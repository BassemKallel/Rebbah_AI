import React, { useState } from 'react';
import { NavLink, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import MainLayout from '../../components/layout/MainLayout';
import BotConfiguration from './tabs/BotConfiguration';
import ResponseIntent from './tabs/ResponseIntent';
import MissingEntities from './tabs/MissingEntities';

import {
  Settings as GenIcon,
  MessageCircle as ResponseIcon,
  AlertCircle as MissingIcon,
  ChevronDown,
  ChevronRight,
  Hand,
  ShoppingCart,
  Tag,
  Package,
  Truck,
  XCircle,
  HelpCircle,
  Info,
  SlidersHorizontal,
  X,
} from 'lucide-react';

const responseIntents = [
  { key: 'greeting',          label: 'Greeting',          Icon: Hand,          vars: ['shop_name', 'ai_agent_name'] },
  { key: 'order-product',     label: 'Order Product',     Icon: ShoppingCart,  vars: ['product'] },
  { key: 'ask-price',         label: 'Ask Price',         Icon: Tag,           vars: ['product', 'price'] },
  { key: 'ask-availability',  label: 'Ask Availability',  Icon: Package,       vars: ['product'] },
  { key: 'ask-delivery',      label: 'Ask Delivery',      Icon: Truck,         vars: ['shop_name'] },
  { key: 'cancel-order',      label: 'Cancel Order',      Icon: XCircle,       vars: [] },
  { key: 'unknown',           label: 'Unknown Intent',    Icon: HelpCircle,    vars: [] },
  { key: 'inform-info',       label: 'Inform Info',       Icon: Info,          vars: [] },
];

const navItems = [
  { id: 'bot_config', label: 'Bot Configuration', icon: <GenIcon className="w-4 h-4" />, path: 'bot-configuration' },
];

const NavSection = ({ label, icon, basePath, subItems, location, onNavClick }: any) => {
  const isActive = location.pathname.includes(basePath);
  const [expanded, setExpanded] = useState(isActive);

  return (
    <div className="flex flex-col">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center justify-between gap-4 px-4 py-3 rounded-xl transition-all font-bold text-[15px]
          ${isActive ? 'bg-[#0f6885] text-white shadow-sm' : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'}`}
      >
        <div className="flex items-center gap-4">{icon}<span>{label}</span></div>
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>
      {expanded && (
        <div className="ml-8 mt-1 flex flex-col gap-1">
          {subItems.map((item: any) => (
            <NavLink
              key={item.key}
              to={`/settings/${basePath}/${item.key}`}
              onClick={onNavClick}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3.5 py-2 rounded-lg transition-all font-semibold text-[13px]
                ${isActive ? 'bg-[#eef6f9] text-[#0f6885]' : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'}`
              }
            >
              {item.Icon && <item.Icon className="w-3.5 h-3.5 flex-shrink-0" />}
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
};

const AgentSettingsLayout = () => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const closeMenu = () => setMobileMenuOpen(false);

  /* ── Navigation links (shared between desktop sidebar & mobile drawer) ── */
  const NavLinks = ({ onNavClick }: { onNavClick?: () => void }) => (
    <nav className="flex-1 w-full flex flex-col px-4 gap-1 overflow-y-auto scrollbar-thin">
      {navItems.map((item) => (
        <NavLink
          key={item.id}
          to={`/settings/${item.path}`}
          onClick={onNavClick}
          className={({ isActive }) =>
            `flex items-center gap-4 px-4 py-3 rounded-xl transition-all font-bold text-[15px]
            ${isActive ? 'bg-[#0f6885] text-white shadow-sm' : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'}`
          }
        >
          {item.icon}{item.label}
        </NavLink>
      ))}
      <NavSection
        label="Responses"
        icon={<ResponseIcon className="w-4 h-4" />}
        basePath="responses"
        subItems={responseIntents}
        location={location}
        onNavClick={onNavClick}
      />
      <NavLink
        to="/settings/missing-entities"
        onClick={onNavClick}
        className={({ isActive }) =>
          `flex items-center gap-4 px-4 py-3 rounded-xl transition-all font-bold text-[15px]
          ${isActive ? 'bg-[#0f6885] text-white shadow-sm' : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'}`
        }
      >
        <MissingIcon className="w-4 h-4" />Missing Entities
      </NavLink>
    </nav>
  );

  /* ── Desktop sidebar content (passed as secondarySidebar) ── */
  const desktopSidebar = (
    <div className="h-full flex flex-col pt-5">
      <div className="px-6 mb-6">
        <h2 className="text-[22px] font-extrabold text-[#1f2937]">Agent settings</h2>
      </div>
      <NavLinks />
    </div>
  );

  return (
    <>
      {/* ── Mobile Drawer Overlay ── */}
      {mobileMenuOpen && (
        <div className="drawer-backdrop md:hidden" onClick={closeMenu} aria-hidden="true" />
      )}

      {/* ── Mobile slide-in drawer ── */}
      <div className={`
        md:hidden fixed inset-y-0 left-0 z-50
        w-[280px] bg-white border-r border-gray-100 shadow-panel
        transition-transform duration-200 ease-in-out
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="h-full flex flex-col pt-5">
          <div className="px-6 mb-6 flex items-center justify-between">
            <h2 className="text-xl font-extrabold text-[#1f2937]">Agent settings</h2>
            <button onClick={closeMenu} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
          <NavLinks onNavClick={closeMenu} />
        </div>
      </div>

      {/* ── Main layout (desktop sidebar hidden on mobile via MainLayout fix) ── */}
      <MainLayout secondarySidebar={desktopSidebar}>
        <div className="h-full flex flex-col bg-white">

          {/* Mobile top bar — "Settings" button to open drawer */}
          <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-gray-100 bg-white flex-shrink-0">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-[#0f6885] bg-[#eef6f9] rounded-xl hover:bg-[#dceef5] transition-colors"
            >
              <SlidersHorizontal className="w-4 h-4" />
              Paramètres
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto scrollbar-thin px-4 sm:px-6 lg:px-10 py-5 sm:py-8">
            <Routes>
              <Route path="/" element={<Navigate to="bot-configuration" replace />} />
              <Route path="bot-configuration" element={<BotConfiguration />} />
              {responseIntents.map((intent) => (
                <Route
                  key={intent.key}
                  path={`responses/${intent.key}`}
                  element={<ResponseIntent intentKey={intent.key} intentConfig={intent} />}
                />
              ))}
              <Route path="missing-entities" element={<MissingEntities />} />
            </Routes>
          </div>
        </div>
      </MainLayout>
    </>
  );
};

export default AgentSettingsLayout;
