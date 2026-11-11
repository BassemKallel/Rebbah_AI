import React, { useState } from 'react';
import BotConfiguration from './BotConfiguration';
import ProductSync from './ProductSync';
import { Settings, Image as ImageIcon, Sparkles } from 'lucide-react';

const AgentDashboard = () => {
  const [activeTab, setActiveTab] = useState('config');

  return (
    <div className="flex h-full w-full bg-gray-50">
      
      {/* ── Local Sidebar ── */}
      <div className="w-72 bg-white border-r border-gray-200 flex-shrink-0 flex flex-col pt-8 px-4 h-full">
        <div className="mb-8 px-3">
          <h1 className="text-[20px] font-extrabold text-gray-900 flex items-center gap-2 tracking-tight">
            <Sparkles className="w-5 h-5 text-[#0f6885]" />
            Tableau de bord IA
          </h1>
          <p className="text-gray-500 mt-1.5 font-medium text-[13px] leading-relaxed">
            Gérez votre agent et sa base de connaissances
          </p>
        </div>

        <div className="flex flex-col gap-1.5 flex-1">
          <h2 className="text-[11px] font-extrabold text-gray-400 uppercase tracking-widest px-3 mb-2">Menu</h2>
          
          <button
            onClick={() => setActiveTab('config')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-200 text-left ${
              activeTab === 'config'
                ? 'bg-[#0f6885]/10 text-[#0f6885]'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Settings className={`w-4 h-4 ${activeTab === 'config' ? 'opacity-100' : 'opacity-70 text-gray-400'}`} />
            Configuration du Bot
          </button>
          
          <button
            onClick={() => setActiveTab('catalog')}
            className={`flex items-center gap-3 px-3 py-3 rounded-xl font-bold text-sm transition-all duration-200 text-left ${
              activeTab === 'catalog'
                ? 'bg-[#0f6885]/10 text-[#0f6885]'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <ImageIcon className={`w-4 h-4 ${activeTab === 'catalog' ? 'opacity-100' : 'opacity-70 text-gray-400'}`} />
            Catalogue Visuel RAG
          </button>
        </div>
      </div>

      {/* ── Main Content Area ── */}
      <div className="flex-1 overflow-y-auto w-full h-full p-8 md:p-12 animate-in fade-in duration-300">
        <div className="max-w-5xl mx-auto w-full">
          {activeTab === 'config' && <BotConfiguration />}
          {activeTab === 'catalog' && <ProductSync />}
        </div>
      </div>

    </div>
  );
};

export default AgentDashboard;
