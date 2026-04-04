import React from 'react';
import { RefreshCcw, ShoppingBag, ShoppingCart, CheckCircle, ExternalLink } from 'lucide-react';

const ProductSync = () => {
  return (
    <div className="max-w-4xl">
      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Product Sync</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">Connect your catalog to enable the AI agent to answer product specific questions and recommend items.</p>
      
      <div className="grid grid-cols-2 gap-6 mb-8">
         {/* Shopify Connect Card */}
         <div className="bg-white border border-gray-100 rounded-2xl p-6 shadow-sm flex flex-col">
            <div className="flex items-center justify-between mb-4">
               <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
                  <ShoppingBag className="w-6 h-6" />
               </div>
               <span className="bg-gray-100 text-gray-500 text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded">Not Connected</span>
            </div>
            <h3 className="text-lg font-bold text-gray-800 mb-1">Shopify</h3>
            <p className="text-sm font-medium text-gray-400 mb-6 flex-1">Automatically sync your products, variants, and inventory levels in real-time.</p>
            <button className="w-full bg-white border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors rounded-xl py-2.5 font-bold text-sm text-gray-700 shadow-sm">
               Connect Shopify
            </button>
         </div>

         {/* WooCommerce Connect Card (Active) */}
         <div className="bg-white border-2 border-[#0f6885]/20 rounded-2xl p-6 shadow-sm flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-[#0f6885]/5 rounded-bl-[100px] -z-10" />
            <div className="flex items-center justify-between mb-4">
               <div className="w-12 h-12 rounded-xl bg-[#eef6f9] text-[#0f6885] flex items-center justify-center border border-[#0f6885]/20">
                  <ShoppingCart className="w-6 h-6" />
               </div>
               <span className="flex items-center gap-1 text-emerald-600 bg-emerald-50 border border-emerald-100 text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded">
                  <CheckCircle className="w-3 h-3" /> Active
               </span>
            </div>
            <h3 className="text-lg font-bold text-gray-800 mb-1">WooCommerce</h3>
            <p className="text-sm font-medium text-gray-400 mb-6 flex-1">Store connected successfully. Products are mapped to your AI agent.</p>
            
            <div className="bg-gray-50 rounded-xl p-3 mb-4 flex justify-between items-center border border-gray-100">
               <div className="flex flex-col">
                 <span className="text-[11px] text-gray-500 font-bold uppercase tracking-wider">Total Synced</span>
                 <span className="text-base font-extrabold text-gray-800">1,245 Products</span>
               </div>
               <div className="flex flex-col text-right">
                 <span className="text-[11px] text-gray-500 font-bold uppercase tracking-wider">Last Sync</span>
                 <span className="text-sm font-bold text-gray-800">2 hours ago</span>
               </div>
            </div>

            <div className="flex gap-2">
               <button className="flex-1 bg-white border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-colors rounded-xl py-2 font-bold text-sm text-gray-700 shadow-sm">
                 Settings
               </button>
               <button className="flex-1 bg-[#0f6885] hover:bg-[#0c5973] transition-colors rounded-xl py-2 font-bold text-sm text-white shadow-sm flex items-center justify-center gap-1.5">
                 <RefreshCcw className="w-4 h-4" /> Sync Now
               </button>
            </div>
         </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-2xl p-5 flex items-center justify-between">
         <div className="flex flex-col">
            <h4 className="text-[15px] font-bold text-gray-800">Custom Integration</h4>
            <p className="text-sm text-gray-500 font-medium">Have a custom built store? Use our API to push catalog updates.</p>
         </div>
         <button className="flex items-center gap-1.5 text-sm font-bold text-[#0f6885] hover:underline">
            View API Docs <ExternalLink className="w-4 h-4" />
         </button>
      </div>

    </div>
  );
};

export default ProductSync;
