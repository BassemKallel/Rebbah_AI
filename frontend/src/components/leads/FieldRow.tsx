import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface FieldRowProps {
  icon: LucideIcon;
  label: string;
  value: string;
  name: string;
  type?: string;
  editing: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const FieldRow: React.FC<FieldRowProps> = ({ icon: Icon, label, value, name, type = 'text', editing, onChange }) => (
  <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
    <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
      <Icon className="w-3.5 h-3.5 text-gray-500" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      {editing ? (
        <input
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          className="w-full text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#0f6885] transition-colors"
        />
      ) : (
        <p className="text-sm font-semibold text-gray-700 truncate">{value || <span className="text-gray-300 font-normal">—</span>}</p>
      )}
    </div>
  </div>
);

export default FieldRow;
