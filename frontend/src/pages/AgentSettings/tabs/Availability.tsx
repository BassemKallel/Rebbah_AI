import React, { useState } from 'react';
import DynamicTemplate from '../components/DynamicTemplate';

const Availability = () => {
  const [loading, setLoading] = useState(false);
  const [agentName] = useState("Street Wear Agent");
  const availableVars = ['{product_name}', '{size_available}', '{color_list}', '{stock_status}', '{agent_name}'];

  const handleSave = async (template) => {
    setLoading(true);
    const payload = {
      page_type: "availability",
      template_string: template,
      agent_name: agentName
    };
    console.log("Saving Availability:", payload);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    alert("Availability configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Availability & Size Guide</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Help customers find the right product in the right size.</p>

      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5 bg-white">
        <h3 className="text-base font-bold text-gray-800">Size Guide & Stock</h3>
        <DynamicTemplate 
          initialValue="Regarding {product_name}, the available sizes are: {size_available}. Colors: {color_list}. Status: {stock_status}."
          availableVars={availableVars}
          onSave={handleSave}
          isLoading={loading}
          label="Response Template"
        />
      </div>
    </div>
  );
};

export default Availability;
