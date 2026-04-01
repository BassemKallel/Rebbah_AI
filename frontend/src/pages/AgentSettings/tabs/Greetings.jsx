import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import CustomToggle from '../components/CustomToggle';
import DynamicTemplate from '../components/DynamicTemplate';

const Greetings = () => {
  const [welcomeEnabled, setWelcomeEnabled] = useState(true);
  const [returningEnabled, setReturningEnabled] = useState(true);
  const [afterHoursEnabled, setAfterHoursEnabled] = useState(true);
  
  const [agentName, setAgentName] = useState("Street Wear Agent");
  const [isSaving, setIsSaving] = useState(false);

  const availableVars = ['{customer_name}', '{store_name}', '{current_time}', '{agent_name}'];

  const handleSave = async (templateStr) => {
    setIsSaving(true);
    const payload = {
      page_type: "greetings",
      template_string: templateStr,
      agent_name: agentName
    };
    console.log("Saving to backend:", payload);
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
    alert("Greeting configuration saved!");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Greeting Messages</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Customize how your AI agent greets customers when they start a conversation.</p>

      {/* Display Name Section */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-3">
        <label className="text-sm font-semibold text-gray-500">Agent Display Name</label>
        <div className="bg-[#f0f4f8] rounded-xl px-4 py-3 border border-transparent hover:border-gray-200 transition-all">
           <input 
             type="text"
             value={agentName}
             onChange={(e) => setAgentName(e.target.value)}
             className="bg-transparent border-none outline-none text-gray-700 font-medium text-sm w-full"
           />
        </div>
      </div>

      {/* Welcome Message Card */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setWelcomeEnabled(!welcomeEnabled)}>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-gray-800">Welcome Message</h3>
              <span className="bg-[#0f6885] text-white text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wide">Required</span>
            </div>
            <p className="text-sm text-gray-400 font-medium mt-0.5">Greeting for customers who have chatted before</p>
          </div>
          <div className="flex items-center gap-3">
            <CustomToggle checked={welcomeEnabled} onChange={(val) => setWelcomeEnabled(val)} />
            <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${welcomeEnabled ? 'rotate-180' : ''}`} />
          </div>
        </div>
        
        {welcomeEnabled && (
          <div className="flex flex-col gap-3">
             <label className="text-sm font-semibold text-gray-500">Response Template</label>
             <DynamicTemplate 
               initialValue="Hello! I'm your personal AI Assistant 🤖. How can I help you today?" 
               availableVars={availableVars}
               isLoading={isSaving}
               onSave={handleSave}
             />
          </div>
        )}
      </div>

      {/* Returning Customer Section */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-5">
         <div className="flex items-center justify-between cursor-pointer" onClick={() => setReturningEnabled(!returningEnabled)}>
            <div>
               <h3 className="text-base font-bold text-gray-800">Returning Customer</h3>
               <p className="text-sm text-gray-400 font-medium mt-0.5">Greeting for customers who have chatted before</p>
            </div>
            <div className="flex items-center gap-3">
               <CustomToggle checked={returningEnabled} onChange={(val) => setReturningEnabled(val)} />
               <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${returningEnabled ? 'rotate-180' : ''}`} />
            </div>
         </div>

         {returningEnabled && (
          <div className="flex flex-col gap-3">
             <label className="text-sm font-semibold text-gray-500">Response Template</label>
             <DynamicTemplate 
               initialValue="Welcome back, {{customer_name}}! Great to see you again. How can I assist you today?" 
               availableVars={availableVars}
               isLoading={isSaving}
               onSave={handleSave}
             />
          </div>
        )}
      </div>

      {/* After Hours Section */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 flex flex-col gap-5">
         <div className="flex items-center justify-between cursor-pointer" onClick={() => setAfterHoursEnabled(!afterHoursEnabled)}>
            <div>
               <h3 className="text-base font-bold text-gray-800">After Hours</h3>
               <p className="text-sm text-gray-400 font-medium mt-0.5">Auto-reply when outside business hours</p>
            </div>
            <div className="flex items-center gap-3">
               <CustomToggle checked={afterHoursEnabled} onChange={(val) => setAfterHoursEnabled(val)} />
               <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${afterHoursEnabled ? 'rotate-180' : ''}`} />
            </div>
         </div>

         {afterHoursEnabled && (
          <div className="flex flex-col gap-3">
             <label className="text-sm font-semibold text-gray-500">Response Template</label>
             <DynamicTemplate 
               initialValue="Hello! Thanks for reaching out. We're currently offline, but I'm here to help with basic questions. Our team will get back to you during business hours." 
               availableVars={availableVars}
               isLoading={isSaving}
               onSave={handleSave}
             />
          </div>
        )}
      </div>
      
    </div>
  );
};

export default Greetings;
