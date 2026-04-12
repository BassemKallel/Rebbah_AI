import React from 'react';
import { Send, Bot } from 'lucide-react';

interface ChatInputProps {
  draft: string;
  onDraftChange: (value: string) => void;
  onSend?: () => void;
  /** Enables the input — only true when human has taken over */
  isHumanControlled?: boolean;
}

const ChatInput: React.FC<ChatInputProps> = ({
  draft, onDraftChange, onSend, isHumanControlled = false,
}) => {
  const canSend = isHumanControlled && draft.trim().length > 0;

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && canSend) {
      e.preventDefault();
      onSend?.();
    }
  };

  return (
    <div className="p-6 bg-[#f8fafc] border-t border-transparent shrink-0 flex flex-col items-center gap-2 pb-8">
      {!isHumanControlled && (
        <p className="text-xs text-gray-400 flex items-center gap-1.5">
          <Bot className="w-3.5 h-3.5" />
          Le bot répond automatiquement · Cliquez sur «&nbsp;Prendre le relais&nbsp;» pour répondre
        </p>
      )}
      <div className={`bg-white border rounded-[28px] w-[95%] shadow-sm px-4 py-3 flex items-center gap-3 transition-all ${
        isHumanControlled
          ? 'border-[#0f6885] ring-2 ring-[#0f6885]/10'
          : 'border-gray-200 opacity-60'
      }`}>
        <input
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isHumanControlled}
          placeholder={isHumanControlled ? 'Écrire un message...' : 'Le bot répond automatiquement…'}
          className="flex-1 bg-transparent text-[15px] font-medium placeholder-gray-400 text-gray-800 outline-none disabled:cursor-not-allowed"
        />
        <button
          disabled={!canSend}
          onClick={onSend}
          className="bg-[#0f6885] hover:bg-[#0c5973] transition-colors rounded-full flex items-center gap-2 px-5 py-2.5 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="font-semibold text-sm">Envoyer</span>
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
