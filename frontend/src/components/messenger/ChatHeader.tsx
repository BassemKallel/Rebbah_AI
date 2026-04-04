import React from 'react';
import { MessageCircle, ArrowLeft, RefreshCw } from 'lucide-react';

interface ChatHeaderProps {
  name: string;
  onRefresh: () => void;
  /** Called when the mobile back button is pressed — optional */
  onBack?: () => void;
}

const ChatHeader: React.FC<ChatHeaderProps> = ({ name, onRefresh, onBack }) => (
  <div className="px-4 sm:px-8 py-3 sm:py-4 bg-white border-b border-gray-100 flex items-center gap-3 flex-shrink-0">

    {/* Back button — mobile only */}
    {onBack && (
      <button
        onClick={onBack}
        className="md:hidden p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors flex-shrink-0"
        aria-label="Retour à la liste"
      >
        <ArrowLeft className="w-5 h-5" />
      </button>
    )}

    {/* Avatar */}
    <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    </div>

    {/* Name */}
    <div className="min-w-0 flex-1">
      <p className="font-bold text-[#1f2937] text-sm truncate">{name}</p>
      <p className="text-xs text-gray-400 flex items-center gap-1">
        <MessageCircle className="w-3 h-3 flex-shrink-0" /> Messenger
      </p>
    </div>

    {/* Refresh */}
    <button
      onClick={onRefresh}
      className="ml-auto flex items-center gap-1.5 text-xs font-medium text-[#0f6885] hover:text-[#0d5a72] transition-colors flex-shrink-0"
      aria-label="Rafraîchir les messages"
    >
      <RefreshCw className="w-3.5 h-3.5" />
      <span className="hidden sm:inline">Rafraîchir</span>
    </button>
  </div>
);

export default ChatHeader;
