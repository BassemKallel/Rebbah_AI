import React from 'react';

const CustomToggle = ({ checked, onChange }) => {
  return (
    <div 
      onClick={() => onChange(!checked)}
      className={`w-11 h-6 flex items-center rounded-full p-1 cursor-pointer transition-colors ${checked ? 'bg-[#0f6885]' : 'bg-gray-300'}`}
    >
      <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
    </div>
  );
};

export default CustomToggle;
