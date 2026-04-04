import React from 'react';
import { TrendingUp, ArrowRight } from 'lucide-react';
import type { ActivityItem } from '../../types';

interface RecentActivityProps {
  items: ActivityItem[];
}

const RecentActivity: React.FC<RecentActivityProps> = ({ items }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-100">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-[#0f6885]" />
        <h3 className="font-bold text-gray-800 text-sm">Recent Activity</h3>
      </div>
      <a href="/analytics" className="flex items-center gap-1 text-xs text-[#0f6885] font-semibold hover:underline">
        View All <ArrowRight className="w-3 h-3" />
      </a>
    </div>
    <div className="divide-y divide-gray-50">
      {items.map((item) => (
        <div key={item.id} className="flex items-center gap-3 sm:gap-4 px-4 sm:px-6 py-3 hover:bg-gray-50 transition-colors">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${item.iconCls}`}>
            <item.Icon className="w-4 h-4" />
          </div>
          <p className="flex-1 text-sm text-gray-700 min-w-0 truncate">{item.text}</p>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full hidden xs:inline-block ${item.cls}`}>{item.state}</span>
            <span className="text-[11px] text-gray-400 whitespace-nowrap">{item.time}</span>
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default RecentActivity;
