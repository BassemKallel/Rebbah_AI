import React from 'react';
import { Search, Plus, MessageSquarePlus } from 'lucide-react';

const mockQuestions = [
  { id: 1, date: '10 mins ago', customer: 'Sarah L.', question: 'Do you ship to Tunisia?', status: 'unanswered' },
  { id: 2, date: '2 hours ago', customer: 'Ahmed M.', question: 'Can I return the hoodie if it does not fit?', status: 'unanswered' },
  { id: 3, date: 'Yesterday', customer: 'Unknown', question: 'Are the sneakers original?', status: 'unanswered' },
];

const QnA = () => {
  return (
    <div className="max-w-4xl">
      <div className="flex items-start justify-between mb-8">
         <div>
            <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Q&A Fine-Tuning</h1>
            <p className="text-[15px] font-medium text-gray-400">Provide manual answers to unanswered questions to train your agent.</p>
         </div>
         <button className="bg-[#0f6885] hover:bg-[#0c5973] transition-colors rounded-xl flex items-center justify-center gap-2 px-4 py-2.5 text-white shadow-sm">
            <Plus className="w-4 h-4" />
            <span className="font-semibold text-sm">Add Q&A Pair</span>
         </button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-6">
         <div className="relative flex-1 max-w-sm">
           <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
           <input
             type="text"
             placeholder="Search questions..."
             className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0f6885]/30 focus:border-[#0f6885] transition-colors placeholder-gray-400 shadow-sm"
           />
         </div>
         <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-xl p-1 shadow-sm">
            <button className="px-3 py-1.5 text-sm font-bold bg-gray-100 text-gray-800 rounded-lg">Unanswered (3)</button>
            <button className="px-3 py-1.5 text-sm font-bold text-gray-500 hover:text-gray-800 rounded-lg transition-colors">Answered (128)</button>
         </div>
      </div>
      
      {/* QnA List */}
      <div className="bg-white border border-gray-100 shadow-sm rounded-2xl overflow-hidden">
        <div className="grid grid-cols-12 gap-4 border-b border-gray-100 bg-gray-50/50 px-6 py-3.5 text-xs font-bold text-gray-500 uppercase tracking-wider">
           <div className="col-span-3">Date / Customer</div>
           <div className="col-span-6">Customer Question</div>
           <div className="col-span-3 text-right">Action</div>
        </div>

        <div className="flex flex-col">
           {mockQuestions.map((item, idx) => (
             <div key={item.id} className={`grid grid-cols-12 gap-4 items-center px-6 py-4 transition-colors hover:bg-gray-50/50 ${idx !== mockQuestions.length - 1 ? 'border-b border-gray-50' : ''}`}>
               <div className="col-span-3 flex flex-col">
                 <span className="text-sm font-medium text-gray-400">{item.date}</span>
                 <span className="text-sm font-semibold text-gray-800">{item.customer}</span>
               </div>
               <div className="col-span-6">
                 <p className="text-[15px] text-gray-800 font-medium leading-relaxed">"{item.question}"</p>
               </div>
               <div className="col-span-3 flex justify-end">
                 <button className="text-[#0f6885] bg-[#eef6f9] hover:bg-[#d6ecf3] transition-colors px-3 py-1.5 rounded-lg flex items-center gap-1.5 border border-[#0f6885]/10">
                    <MessageSquarePlus className="w-4 h-4" />
                    <span className="text-sm font-bold">Provide Answer</span>
                 </button>
               </div>
             </div>
           ))}
        </div>
      </div>

    </div>
  );
};

export default QnA;
