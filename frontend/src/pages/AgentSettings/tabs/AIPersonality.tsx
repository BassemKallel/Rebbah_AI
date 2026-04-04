import React, { useState } from 'react';
import CustomToggle from '../components/CustomToggle';

const AIPersonality = () => {
  const [useEmojis, setUseEmojis] = useState(true);
  const [matchLanguage, setMatchLanguage] = useState(true);

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">AI Personality</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Define the tone, style, and behavior of your AI agent.</p>

      {/* Tone & Style */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-3">
        <label className="text-base font-bold text-gray-800">Tone & Style</label>
        <div className="bg-[#f0f4f8] rounded-xl px-4 py-3 cursor-pointer border border-transparent hover:border-gray-200 transition-colors">
          <span className="text-gray-800 font-medium text-[15px]">Formal</span>
        </div>
      </div>

      {/* Custom Instructions */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col gap-5 bg-white">
         <div className="flex items-center gap-3">
           <div className="w-5 h-5 rounded-md bg-[#fed7aa] flex-shrink-0" />
           <h3 className="text-base font-bold text-gray-800">Custom Instructions</h3>
         </div>

         <div className="flex flex-col gap-2">
           <label className="text-[13px] font-semibold text-gray-600">Additional Context for AI</label>
           <textarea 
               rows={4} 
               placeholder="eg..."
               className="w-full bg-[#f8fafc] border border-gray-100 rounded-xl p-4 text-sm text-gray-700 font-medium resize-none focus:outline-none focus:ring-2 focus:ring-[#0f6885]/20 focus:border-[#0f6885] transition-colors"
           />
         </div>

         <div className="flex flex-col gap-0 border border-gray-100 rounded-xl overflow-hidden mt-2">
            <div className="flex items-center justify-between px-5 py-3.5 bg-white border-b border-gray-100 hover:bg-gray-50 transition-colors">
               <span className="font-semibold text-gray-800 text-sm">Use Emojis in responses</span>
               <CustomToggle checked={useEmojis} onChange={setUseEmojis} />
            </div>
            <div className="flex items-center justify-between px-5 py-3.5 bg-white hover:bg-gray-50 transition-colors">
               <span className="font-semibold text-gray-800 text-sm">Match customer's language</span>
               <CustomToggle checked={matchLanguage} onChange={setMatchLanguage} />
            </div>
         </div>
      </div>
      
    </div>
  );
};

export default AIPersonality;
