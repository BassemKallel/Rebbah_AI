import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { KpiData } from '../../types';
import Sparkline from './Sparkline';

interface KpiCardProps {
  k: KpiData;
}

const KpiCard: React.FC<KpiCardProps> = ({ k }) => (
  <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between">
      <div className={`w-10 h-10 rounded-xl ${k.bg} ${k.text} flex items-center justify-center`}>
        {k.icon}
      </div>
      <Sparkline data={k.sparkline} up={k.up} />
    </div>
    <div>
      <p className="text-xs text-gray-500 font-medium">{k.label}</p>
      <p className="text-3xl font-extrabold text-gray-900 mt-0.5 tracking-tight">{k.value}</p>
    </div>
    <div className="flex items-center gap-1.5">
      <span className={`flex items-center gap-0.5 text-xs font-bold ${k.up ? 'text-emerald-600' : 'text-orange-500'}`}>
        {k.up ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
        {k.delta}
      </span>
      <span className="text-xs text-gray-400">{k.sub}</span>
    </div>
  </div>
);

export default KpiCard;
