import React, { useState } from 'react';
import { Upload, UserCircle, Palette } from 'lucide-react';

const Appearance = () => {
  const [agentName, setAgentName] = useState("Street Wear Agent");

  const colors = [
    '#0f6885',  // Dark blue
    '#4b5563',  // Gray
    '#f97316',  // Orange
    '#eab308',  // Yellow
    '#1f2937',  // Very dark
    '#cbd5e1',  // Light gray
    '#57534e',  // Brown/Gray
    '#0ea5e9',  // Sky blue
    '#e2e8f0',  // Very light gray
  ];

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Appearance</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Customize the look and feel of your chat widget.</p>

      {/* Agent Display Name */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-3 bg-white">
        <label className="text-base font-bold text-gray-800">Agent Display Name</label>
        <div className="bg-[#f0f4f8] rounded-xl px-4 py-3 border border-transparent hover:border-gray-200 transition-colors flex items-center">
          <input 
             type="text"
             value={agentName}
             onChange={(e) => setAgentName(e.target.value)}
             className="bg-transparent border-none outline-none text-gray-800 font-medium text-[15px] w-full"
           />
        </div>
      </div>

      {/* Agent & Avatar */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-4 bg-white">
         <div className="flex items-center gap-3">
           <UserCircle className="w-5 h-5 text-[#0f6885]" />
           <h3 className="text-base font-bold text-gray-800">Agent & Avatar</h3>
         </div>

         <div className="flex items-center gap-4 mt-2">
            <div className="w-10 h-10 rounded-full bg-[#f8fafc] border border-gray-200 flex items-center justify-center text-[#0f6885] hover:bg-gray-50 cursor-pointer">
               <Upload className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
               <span className="text-sm font-semibold text-gray-800">Upload your agent's avatar</span>
               <span className="text-xs font-medium text-gray-400 mt-0.5">PNG, JPG up to 2MB. Recommended 200*200px</span>
            </div>
         </div>
      </div>

      {/* Agent Display Color */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col gap-5 bg-white">
         <div className="flex items-center gap-3">
           <Palette className="w-5 h-5 text-[#0f6885]" />
           <h3 className="text-base font-bold text-gray-800">Agent Display Color</h3>
         </div>

         <div className="flex flex-wrap gap-4 mt-2">
            {colors.map((color, idx) => (
               <div 
                  key={color} 
                  className={`w-[70px] h-[65px] rounded-[18px] cursor-pointer shadow-sm border-2 transform transition-transform hover:scale-105 ${idx === 0 ? 'border-white ring-2 ring-gray-200' : 'border-transparent'}`}
                  style={{ backgroundColor: color }}
               />
            ))}
         </div>
      </div>
      
    </div>
  );
};

export default Appearance;
