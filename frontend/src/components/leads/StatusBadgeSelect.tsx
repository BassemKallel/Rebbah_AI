import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Loader } from 'lucide-react';
import type { Lead, LeadStatus } from '../../types';
import { STATUS_OPTIONS, STATUS_COLORS } from '../../constants/leads';
import { getStatusValue } from '../../utils/leads';

interface StatusBadgeSelectProps {
  lead: Lead;
  onChange: (value: LeadStatus) => void;
  loading: boolean;
}

const StatusBadgeSelect: React.FC<StatusBadgeSelectProps> = ({ lead, onChange, loading }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = getStatusValue(lead);
  const opt = STATUS_OPTIONS.find((o) => o.value === current);
  const colors = STATUS_COLORS[current];

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (loading) return (
    <div className="px-2 py-1"><Loader className="w-3.5 h-3.5 animate-spin text-gray-400" /></div>
  );

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-semibold transition-all ${colors.pill} ${colors.hover}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${colors.dot}`} />
        {opt?.label}
        <ChevronDown className={`w-3 h-3 opacity-40 transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-50 bg-white border border-gray-100 rounded-xl shadow-xl py-1 min-w-[170px]">
          {STATUS_OPTIONS.map((o) => {
            const c = STATUS_COLORS[o.value];
            const isActive = o.value === current;
            return (
              <button key={o.value}
                onClick={() => { setOpen(false); if (!isActive) onChange(o.value); }}
                className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-[12px] font-medium transition-colors ${isActive ? 'bg-gray-50 text-gray-400 cursor-default' : 'text-gray-700 hover:bg-gray-50'}`}
              >
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${c.dot}`} />
                {o.label}
                {isActive && <span className="ml-auto text-[10px] text-gray-300">actuel</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default StatusBadgeSelect;
