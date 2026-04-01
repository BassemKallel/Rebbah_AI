import React, { useState } from 'react';
import DynamicTemplate from '../components/DynamicTemplate';

const OrderConfirmation = () => {
  const [loading, setLoading] = useState(false);
  const [agentName] = useState("Street Wear Agent");
  const availableVars = ['{customer_name}', '{order_id}', '{total_amount}', '{delivery_date}', '{agent_name}'];

  const handleSave = async (template) => {
    setLoading(true);
    const payload = {
      page_type: "order_flow",
      template_string: template,
      agent_name: agentName
    };
    console.log("Saving Order Flow:", payload);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setLoading(false);
    alert("Order flow configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Order Flow</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Configure the summary message sent after a successful order.</p>

      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5 bg-white">
        <div className="flex flex-col gap-1">
          <h3 className="text-base font-bold text-gray-800">Summary Template</h3>
          <p className="text-sm text-gray-400 font-medium">Final message detailing the order information.</p>
        </div>

        <DynamicTemplate 
          initialValue="Thank you for your order, {customer_name}! Your order #{order_id} for a total of {total_amount} is being prepared. Estimated delivery: {delivery_date}."
          availableVars={availableVars}
          onSave={handleSave}
          isLoading={loading}
          label="Message Template"
        />
      </div>
    </div>
  );
};

export default OrderConfirmation;
