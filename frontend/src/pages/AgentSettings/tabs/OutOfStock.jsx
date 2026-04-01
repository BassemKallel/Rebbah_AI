import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import CustomToggle from '../components/CustomToggle';
import DynamicTemplate from '../components/DynamicTemplate';

const OutOfStock = () => {
  const [recommendAlternatives, setRecommendAlternatives] = useState(true);
  const [notifyRestock, setNotifyRestock] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [agentName] = useState("Street Wear Agent");

  const standardVars = ['{product_name}', '{customer_name}', '{agent_name}'];
  const altVars = ['{alternative_products}', '{customer_name}', '{agent_name}'];

  const handleSave = async (template) => {
    setIsLoading(true);
    const payload = {
      page_type: "out_of_stock",
      template_string: template,
      agent_name: agentName
    };
    console.log("Saving Out of Stock:", payload);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsLoading(false);
    alert("Out of stock configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Out of Stock Handling</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Define how the AI responds when a requested product is unavailable.</p>

      {/* Out of Stock Response */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5">
        <div className="flex items-center justify-between cursor-pointer">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-800">Standard Response</h3>
              <span className="bg-[#0f6885] text-white text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide">Required</span>
            </div>
            <p className="text-sm text-gray-400 font-medium mt-0.5">Primary message when an item is out of stock</p>
          </div>
          <div className="flex items-center gap-3">
            <CustomToggle checked={true} onChange={() => {}} />
            <ChevronDown className="w-5 h-5 text-gray-400 transition-transform rotate-180" />
          </div>
        </div>
        
        <DynamicTemplate 
          initialValue="Unfortunately, the {product_name} is currently out of stock. We apologize for the inconvenience."
          availableVars={standardVars}
          onSave={handleSave}
          isLoading={isLoading}
        />
      </div>

      {/* Recommend Alternatives */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5">
         <div className="flex items-center justify-between cursor-pointer" onClick={() => setRecommendAlternatives(!recommendAlternatives)}>
            <div>
               <h3 className="text-base font-bold text-gray-800">Recommend Alternatives</h3>
               <p className="text-sm text-gray-400 font-medium mt-0.5">Suggest similar items to the customer</p>
            </div>
            <div className="flex items-center gap-3">
               <CustomToggle checked={recommendAlternatives} onChange={(val) => setRecommendAlternatives(val)} />
               <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${recommendAlternatives ? 'rotate-180' : ''}`} />
            </div>
         </div>

         {recommendAlternatives && (
            <DynamicTemplate 
              initialValue="However, you might be interested in these similar products: {alternative_products}"
              availableVars={altVars}
              onSave={handleSave}
              isLoading={isLoading}
            />
         )}
      </div>

      {/* Notify Restock */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex items-center justify-between">
         <div>
            <h3 className="text-base font-bold text-gray-800">Notify upon Restock</h3>
            <p className="text-sm text-gray-400 font-medium mt-0.5">Ask if they want to be notified when item returns</p>
         </div>
         <div className="flex items-center gap-3">
            <CustomToggle checked={notifyRestock} onChange={setNotifyRestock} />
            <ChevronDown className="w-5 h-5 text-gray-400" />
         </div>
      </div>
    </div>
  );
};

export default OutOfStock;
