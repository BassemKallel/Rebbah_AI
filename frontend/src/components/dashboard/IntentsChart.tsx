import React from 'react';
import { Bot } from 'lucide-react';
import type { IntentData } from '../../types';

interface IntentsChartProps {
  intents: IntentData[];
}

const IntentsChart: React.FC<IntentsChartProps> = ({ intents }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <div className="flex items-center gap-2 px-6 py-4 border-b border-gray-100">
      <Bot className="w-4 h-4 text-[#0f6885]" />
      <h3 className="font-bold text-gray-800 text-sm">Frequent Intents</h3>
    </div>
    <div className="px-6 py-4 space-y-4">
      {intents.map((item) => (
        <div key={item.intent}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-gray-700">{item.intent}</span>
            <span className="text-xs font-bold text-gray-500">{item.count}</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${item.color} transition-all`} style={{ width: `${item.pct}%` }} />
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default IntentsChart;
