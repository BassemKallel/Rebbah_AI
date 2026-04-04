import React, { useState } from 'react';
import DynamicTemplate from '../components/DynamicTemplate';

const ProductInfo = () => {
  const [loading, setLoading] = useState(false);
  const [agentName] = useState("Street Wear Agent");
  const availableVars = ['{product_name}', '{price}', '{description}', '{agent_name}'];

  const handleSave = async (template) => {
    setLoading(true);
    const payload = {
      page_type: "product_info",
      template_string: template,
      agent_name: agentName
    };
    console.log("Saving Product Info:", payload);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(true); // Wait, I should set it to false
    setLoading(false);
    alert("Product Information configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Product Information</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Manage responses for product pricing and descriptions.</p>

      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5 bg-white">
        <h3 className="text-base font-bold text-gray-800">Product Details</h3>
        <DynamicTemplate 
          initialValue="The price of {product_name} is {price}. {description}"
          availableVars={availableVars}
          onSave={handleSave}
          isLoading={loading}
          label="Response Template"
        />
      </div>
    </div>
  );
};

export default ProductInfo;
