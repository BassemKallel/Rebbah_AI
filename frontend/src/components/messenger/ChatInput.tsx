import React from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  draft: string;
  onDraftChange: (value: string) => void;
  onSend?: () => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ draft, onDraftChange, onSend }) => (
  <div className="p-6 bg-[#f8fafc] border-t border-transparent shrink-0 flex justify-center pb-8">
    <div className="bg-white border border-gray-200 rounded-[28px] w-[95%] shadow-sm px-4 py-3 flex items-center gap-3 transition-all focus-within:ring-2 focus-within:ring-[#0f6885]/20 focus-within:border-[#0f6885]">
      <input
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        placeholder="Répondre à ce client…"
        className="flex-1 bg-transparent text-[15px] font-medium placeholder-gray-400 text-gray-800 outline-none"
      />
      <button
        disabled={!draft.trim()}
        onClick={onSend}
        className="bg-[#0f6885] hover:bg-[#0c5973] transition-colors rounded-full flex items-center gap-2 px-5 py-2.5 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className="font-semibold text-sm">Envoyer</span>
        <Send className="w-4 h-4" />
      </button>
    </div>
  </div>
);

export default ChatInput;
