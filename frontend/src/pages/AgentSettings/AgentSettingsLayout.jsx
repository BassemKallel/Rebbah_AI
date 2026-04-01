import React, { useState } from 'react';
import { NavLink, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import MainLayout from '../../components/layout/MainLayout';
import BotConfiguration from './tabs/BotConfiguration';
import ResponseIntent from './tabs/ResponseIntent';
import MissingEntities from './tabs/MissingEntities';

// Icons
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
} from 'lucide-react';

// Response intents configuration
const responseIntents = [
  { key: 'greeting', label: 'Greeting', Icon: Hand, vars: ['shop_name', 'ai_agent_name'] },
  { key: 'order-product', label: 'Order Product', Icon: ShoppingCart, vars: ['product'] },
  { key: 'ask-price', label: 'Ask Price', Icon: Tag, vars: ['product', 'price'] },
  { key: 'ask-availability', label: 'Ask Availability', Icon: Package, vars: ['product'] },
  { key: 'ask-delivery', label: 'Ask Delivery', Icon: Truck, vars: ['shop_name'] },
  { key: 'cancel-order', label: 'Cancel Order', Icon: XCircle, vars: [] },
  { key: 'unknown', label: 'Unknown Intent', Icon: HelpCircle, vars: [] },
  { key: 'inform-info', label: 'Inform Info', Icon: Info, vars: [] },
];

const navItems = [
  { id: 'bot_config', label: 'Bot Configuration', icon: <GenIcon className="w-4 h-4" />, path: 'bot-configuration' },
];

// Reusable sidebar section with expand/collapse and sub-links
const NavSection = ({ label, icon, basePath, subItems, location }) => {
  const isActive = location.pathname.includes(basePath);
  const [expanded, setExpanded] = useState(isActive);

  return (
    <div className="flex flex-col">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`
          flex items-center justify-between gap-4 px-4 py-3.5 rounded-xl transition-all font-bold text-[15px]
          ${isActive
            ? 'bg-[#0f6885] text-white shadow-sm'
            : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'
          }
        `}
      >
        <div className="flex items-center gap-4">
          {icon}
          <span>{label}</span>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {expanded && (
        <div className="ml-8 mt-1 flex flex-col gap-1">
          {subItems.map((item) => (
            <NavLink
              key={item.key}
              to={`/settings/${basePath}/${item.key}`}
              className={({ isActive }) => `
                flex items-center gap-2.5 px-3.5 py-2 rounded-lg transition-all font-semibold text-[13px]
                ${isActive
                  ? 'bg-[#eef6f9] text-[#0f6885]'
                  : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'
                }
              `}
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

  const sidebarContent = (
    <div className="h-full flex flex-col pt-5">
      <div className="px-6 mb-8 flex items-center justify-between">
        <h2 className="text-[22px] font-extrabold text-[#1f2937]">Agent settings</h2>
      </div>

      <nav className="flex-1 w-full flex flex-col px-4 gap-1 overflow-y-auto">
        {/* Static nav items */}
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={`/settings/${item.path}`}
            className={({ isActive }) => `
              flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all font-bold text-[15px]
              ${isActive
                ? 'bg-[#0f6885] text-white shadow-sm'
                : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'
              }
            `}
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}

        {/* Responses section */}
        <NavSection
          label="Responses"
          icon={<ResponseIcon className="w-4 h-4" />}
          basePath="responses"
          subItems={responseIntents}
          location={location}
        />

        {/* Missing Entities — direct link, no sub-menu */}
        <NavLink
          to="/settings/missing-entities"
          className={({ isActive }) => `
            flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all font-bold text-[15px]
            ${isActive
              ? 'bg-[#0f6885] text-white shadow-sm'
              : 'text-gray-500 hover:text-[#0f6885] hover:bg-gray-50'
            }
          `}
        >
          <MissingIcon className="w-4 h-4" />
          Missing Entities
        </NavLink>
      </nav>
    </div>
  );

  return (
    <MainLayout secondarySidebar={sidebarContent}>
      <div className="h-full flex flex-col bg-white">
        <div className="px-10 py-8 flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="bot-configuration" replace />} />
            <Route path="bot-configuration" element={<BotConfiguration />} />

            {/* Response intent routes */}
            {responseIntents.map(intent => (
              <Route
                key={intent.key}
                path={`responses/${intent.key}`}
                element={<ResponseIntent intentKey={intent.key} intentConfig={intent} />}
              />
            ))}

            {/* Missing Entities route */}
            <Route path="missing-entities" element={<MissingEntities />} />
          </Routes>
        </div>
      </div>
    </MainLayout>
  );
};

export default AgentSettingsLayout;
