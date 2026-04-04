import React from 'react';
import { Zap } from 'lucide-react';

const AutomationCard: React.FC = () => (
  <div className="bg-gradient-to-br from-[#0f6885] to-[#0a4f66] rounded-2xl p-6 text-white shadow-sm">
    <div className="flex items-center gap-2 mb-4">
      <Zap className="w-4 h-4 text-white/80" />
      <p className="text-sm font-semibold text-white/80">Automation</p>
    </div>
    <div className="flex items-end justify-between">
      <div>
        <p className="text-5xl font-extrabold tracking-tight">96<span className="text-2xl text-white/70">%</span></p>
        <p className="text-xs text-white/60 mt-1">4 human interventions</p>
      </div>
      <div className="relative w-16 h-16">
        <svg viewBox="0 0 36 36" className="rotate-[-90deg] w-full h-full">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="3" />
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="white" strokeWidth="3"
            strokeDasharray="96 4" strokeLinecap="round" />
        </svg>
        <p className="absolute inset-0 flex items-center justify-center text-[10px] font-bold">96%</p>
      </div>
    </div>
    <div className="mt-4 pt-4 border-t border-white/20 grid grid-cols-2 gap-3">
      <div>
        <p className="text-2xl font-bold">81</p>
        <p className="text-[11px] text-white/60">Conversations</p>
      </div>
      <div>
        <p className="text-2xl font-bold">42</p>
        <p className="text-[11px] text-white/60">Orders</p>
      </div>
    </div>
  </div>
);

export default AutomationCard;
