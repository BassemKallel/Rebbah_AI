import React from 'react';
import type { HourlyData } from '../../types';

interface ConversationVolumeProps {
  data: HourlyData[];
  total: string;
}

const ConversationVolume: React.FC<ConversationVolumeProps> = ({ data, total }) => {
  const maxV = Math.max(...data.map((h) => h.v));
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-card p-4 sm:p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="font-bold text-gray-800 text-sm">Conversation Volume</h3>
          <p className="text-xs text-gray-400">Today — hourly breakdown</p>
        </div>
        <span className="text-xs bg-[#eef6f9] text-[#0f6885] font-semibold px-2.5 py-1 rounded-lg">{total} Total</span>
      </div>
      <div className="flex items-end gap-1.5 h-24">
        {data.map((item) => (
          <div key={item.h} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full rounded-t-md bg-[#0f6885]/80 hover:bg-[#0f6885] transition-colors cursor-default"
              style={{ height: `${(item.v / maxV) * 80}px` }}
              title={`${item.v} conv.`}
            />
            <span className="text-[9px] text-gray-400">{item.h}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ConversationVolume;
