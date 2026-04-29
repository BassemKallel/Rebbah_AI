import React from 'react';
import { TrendingUp, ArrowRight } from 'lucide-react';

interface FunnelStage {
  key: string;
  label: string;
  count: number;
  pct: number;
  color: string;
  color_hex: string;
  sparkline: number[];
}

interface Conversion {
  conv_to_lead: number;
  lead_to_qualified: number;
}

interface LeadFunnelProps {
  stages: FunnelStage[];
  conversion: Conversion;
  total: number;
}

const Sparkbar: React.FC<{ data: number[]; colorHex: string }> = ({ data, colorHex }) => {
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-[2px] h-6 w-16">
      {data.map((v, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm opacity-80"
          style={{
            height: `${Math.max(10, (v / max) * 100)}%`,
            backgroundColor: colorHex,
          }}
        />
      ))}
    </div>
  );
};

const LeadFunnel: React.FC<LeadFunnelProps> = ({ stages, conversion, total }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-100">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-[#0f6885]" />
        <h3 className="font-bold text-gray-800 text-sm">Lead Funnel</h3>
      </div>
      <span className="text-xs bg-[#eef6f9] text-[#0f6885] font-semibold px-2.5 py-1 rounded-lg">
        {total} total
      </span>
    </div>

    <div className="px-4 sm:px-6 py-4 space-y-4">
      {stages.map((stage, i) => (
        <div key={stage.key}>
          {/* Stage row */}
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-700">{stage.label}</span>
              <span className="text-xs text-gray-400 font-medium">{stage.count}</span>
            </div>
            <Sparkbar data={stage.sparkline} colorHex={stage.color_hex} />
          </div>

          {/* Progress bar */}
          <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${stage.color}`}
              style={{ width: `${stage.pct}%` }}
            />
          </div>

          {/* Drop-off arrow between stages */}
          {i < stages.length - 1 && (
            <div className="flex items-center gap-1.5 mt-2 mb-0.5">
              <ArrowRight className="w-3 h-3 text-gray-300" />
              <span className="text-[10px] text-gray-400 font-medium">
                {i === 0
                  ? `${conversion.conv_to_lead}% ont une intention d'achat`
                  : `${conversion.lead_to_qualified}% complètent la commande`}
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  </div>
);

export default LeadFunnel;
