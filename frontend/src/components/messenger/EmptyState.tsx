import React from 'react';
import { MessageCircle } from 'lucide-react';

const EmptyState: React.FC = () => (
  <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#f8fafc]">
    <div className="flex flex-col items-center gap-4">
      <div className="w-20 h-20 rounded-full bg-white border border-gray-100 shadow-sm flex items-center justify-center">
        <MessageCircle className="w-9 h-9 text-[#0f6885]/30" />
      </div>
      <div className="text-center">
        <p className="text-[#1f2937] font-semibold text-base">Sélectionnez une conversation</p>
        <p className="text-gray-400 text-sm mt-1">pour afficher les messages ici</p>
      </div>
    </div>
  </div>
);

export default EmptyState;
