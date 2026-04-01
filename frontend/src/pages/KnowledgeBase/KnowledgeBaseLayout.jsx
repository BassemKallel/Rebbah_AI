import React from 'react';
import { NavLink, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from '../../components/layout/MainLayout';

// Tabs (Placeholders for now)
import QnA from './tabs/QnA';

// Icons
import {
  HelpCircle
} from 'lucide-react';

const navItems = [
  { id: 'qna', label: 'Q&A Fine-Tuning', icon: <HelpCircle className="w-4 h-4" />, path: 'qna' },
];

const KnowledgeBaseLayout = () => {
  const sidebarContent = (
    <div className="h-full flex flex-col pt-5">
      <div className="px-6 mb-8 flex flex-col">
        <h2 className="text-[22px] font-extrabold text-[#1f2937]">Knowledge Base</h2>
        <span className="text-sm font-medium text-gray-400 mt-1">Train your AI Agent</span>
      </div>

      <nav className="flex-1 w-full flex flex-col px-4 gap-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={`/knowledge/${item.path}`}
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
      </nav>
    </div>
  );

  return (
    <MainLayout secondarySidebar={sidebarContent}>
      <div className="h-full flex flex-col bg-white">
        <div className="px-10 py-8 flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="qna" replace />} />
            <Route path="qna" element={<QnA />} />
          </Routes>
        </div>
      </div>
    </MainLayout>
  );
};

export default KnowledgeBaseLayout;
