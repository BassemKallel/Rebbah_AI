import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import CustomToggle from '../components/CustomToggle';
import DynamicTemplate from '../components/DynamicTemplate';

const Complaints = () => {
  const [notifyOwner, setNotifyOwner] = useState(true);
  const [initialResponse, setInitialResponse] = useState(true);
  const [escalateToHuman, setEscalateToHuman] = useState(true);
  const [issueResolved, setIssueResolved] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [agentName] = useState("Street Wear Agent");

  const availableVars = ['{customer_name}', '{order_id}', '{product_name}', '{agent_name}'];

  const handleSave = async (template) => {
    setIsLoading(true);
    const payload = {
      page_type: "complaints",
      template_string: template,
      agent_name: agentName
    };
    console.log("Saving Complaints:", payload);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsLoading(false);
    alert("Complaints configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Complaints Handling</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Configure how the AI handles complaints and escalation to human agents.</p>

      {/* Escalation Settings */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-3">
        <h3 className="text-base font-bold text-gray-800">Escalation Settings</h3>
        
        <div className="flex items-center gap-4">
           <div className="flex-1 bg-[#f0f4f8] rounded-xl px-4 py-3 flex items-center justify-between cursor-pointer border border-transparent hover:border-gray-200 transition-colors">
              <span className="text-gray-800 font-medium text-[15px]">3 Failed Attempts</span>
              <ChevronDown className="w-5 h-5 text-gray-400" />
           </div>
           
           <div className="flex-1 bg-[#f0f4f8] rounded-xl px-4 py-3 flex items-center justify-between border border-transparent hover:border-gray-200 transition-colors">
              <span className="text-gray-800 font-medium text-[15px]">Notify Owner</span>
              <CustomToggle checked={notifyOwner} onChange={setNotifyOwner} />
           </div>
        </div>
      </div>

      {/* Initial Complaint Response */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setInitialResponse(!initialResponse)}>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-800">Initial Complaint Response</h3>
              <span className="bg-[#0f6885] text-white text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide">Required</span>
            </div>
            <p className="text-sm text-gray-400 font-medium mt-0.5">First response when a complaint is detected</p>
          </div>
          <div className="flex items-center gap-3">
            <CustomToggle checked={initialResponse} onChange={(val) => setInitialResponse(val)} />
            <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${initialResponse ? 'rotate-180' : ''}`} />
          </div>
        </div>
        
        {initialResponse && (
          <DynamicTemplate 
            initialValue="I'm sorry to hear that, {customer_name}. I understand your frustration and I want to help resolve this. Could you please provide more details about the issue with order #{order_id}?"
            availableVars={availableVars}
            onSave={handleSave}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Escalation to Human */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex items-center justify-between">
         <div>
            <h3 className="text-base font-bold text-gray-800">Escalation to Human</h3>
            <p className="text-sm text-gray-400 font-medium mt-0.5">When the issue needs human intervention</p>
         </div>
         <div className="flex items-center gap-3">
            <CustomToggle checked={escalateToHuman} onChange={setEscalateToHuman} />
            <ChevronDown className="w-5 h-5 text-gray-400" />
         </div>
      </div>

      {/* Issue Resolved */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex items-center justify-between">
         <div>
            <h3 className="text-base font-bold text-gray-800">Issue Resolved</h3>
            <p className="text-sm text-gray-400 font-medium mt-0.5">Follow-up after resolving a complaint</p>
         </div>
         <div className="flex items-center gap-3">
            <CustomToggle checked={issueResolved} onChange={setIssueResolved} />
            <ChevronDown className="w-5 h-5 text-gray-400" />
         </div>
      </div>
    </div>
  );
};

export default Complaints;
