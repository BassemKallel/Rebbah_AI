import React from 'react';
import { MessageCircle } from 'lucide-react';

interface ChatHeaderProps {
  name: string;
  onRefresh: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ name, onRefresh }) => (
  <div className="px-8 py-4 bg-white border-b border-gray-100 flex items-center gap-3 shrink-0">
    <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>
    <div>
      <p className="font-bold text-[#1f2937] text-sm">{name}</p>
      <p className="text-xs text-gray-400 flex items-center gap-1">
        <MessageCircle className="w-3 h-3" /> Messenger
      </p>
    </div>
    <button onClick={onRefresh} className="ml-auto text-xs text-[#0f6885] hover:underline">
      Rafraîchir
    </button>
  </div>
);

export default ChatHeader;
