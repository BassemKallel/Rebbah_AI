import React, { useState, useEffect } from 'react';
import { Loader2, Save, X } from 'lucide-react';

const DynamicTemplate = ({ initialValue, availableVars, onSave, isLoading, label = "Response Template" }) => {
  const parseStringToBlocks = (str) => {
    if (!str) return [{ id: Math.random(), type: 'text', val: '' }];
    const parts = str.split(/({.*?})/);
    return parts.map((p) => {
      if (p.startsWith('{') && p.endsWith('}')) {
        return { id: Math.random(), type: 'var', val: p };
      }
      return { id: Math.random(), type: 'text', val: p };
    }).filter(p => p.val !== '');
  };

  const [blocks, setBlocks] = useState(parseStringToBlocks(initialValue));
  const [pool, setPool] = useState([]);

  useEffect(() => {
    const usedVars = blocks.filter(b => b.type === 'var').map(b => b.val);
    setPool(availableVars.filter(v => !usedVars.includes(v)));
  }, [blocks, availableVars]);

  const addVar = (v) => {
    setBlocks([...blocks, { id: Math.random(), type: 'var', val: v }, { id: Math.random(), type: 'text', val: '' }]);
  };

  const removeBlock = (id) => {
    setBlocks(blocks.filter(b => b.id !== id));
  };

  const updateText = (id, newVal) => {
    setBlocks(blocks.map(b => b.id === id ? { ...b, val: newVal } : b));
  };

  const exportTemplate = () => {
    return blocks.map(b => b.val).join('');
  };

  return (
    <div className="flex flex-col gap-3">
      <label className="text-sm font-semibold text-gray-500">{label}</label>
      
      {/* Template Area */}
      <div className="flex flex-wrap items-center gap-1.5 w-full bg-[#f8fafc] border border-gray-100 rounded-xl p-4 min-h-[100px] focus-within:ring-2 focus-within:ring-[#0f6885]/10 focus-within:border-[#0f6885] transition-all">
        {blocks.map((block) => (
          block.type === 'var' ? (
            <span 
              key={block.id}
              onClick={() => removeBlock(block.id)}
              className="inline-flex items-center gap-1 px-2 py-1 bg-[#d6ecf3] text-[#0f6885] text-xs font-semibold rounded-md cursor-pointer hover:bg-[#b0e0ef] transition-colors group"
            >
              {block.val}
              <X className="w-3 h-3 group-hover:scale-110 transition-transform" />
            </span>
          ) : (
            <span
              key={block.id}
              contentEditable
              suppressContentEditableWarning
              onBlur={(e) => updateText(block.id, e.target.innerText)}
              className="outline-none text-gray-700 font-medium text-sm min-w-[4px]"
            >
              {block.val}
            </span>
          )
        ))}
      </div>

      {/* Variables Pool */}
      <div className="bg-[#d6ecf3]/30 rounded-xl p-4 border border-gray-50 flex flex-col gap-2">
        <div className="flex items-center gap-1.5 text-[#0f6885]">
          <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          <span className="text-xs font-bold">Available variables:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {pool.map((v) => (
            <button
              key={v}
              onClick={() => addVar(v)}
              className="text-xs font-semibold text-[#0f6885] bg-[#d6ecf3] px-2.5 py-1 rounded-md hover:bg-[#b0e0ef] transition-colors cursor-pointer"
            >
              {v}
            </button>
          ))}
          {pool.length === 0 && (
            <span className="text-xs text-gray-400 font-medium italic">All variables in use</span>
          )}
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end mt-2">
        <button 
          onClick={() => onSave(exportTemplate())}
          disabled={isLoading}
          className="bg-[#0f6885] hover:bg-[#0d5a74] disabled:bg-gray-300 text-white text-sm font-bold py-2.5 px-6 rounded-xl flex items-center gap-2 shadow-sm transition-all active:scale-95"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          <span>Save Changes</span>
        </button>
      </div>
    </div>
  );
};

export default DynamicTemplate;
