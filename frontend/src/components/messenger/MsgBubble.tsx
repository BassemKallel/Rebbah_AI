import React from 'react';
import { AlertCircle } from 'lucide-react';
import type { Message } from '../../types';
import { isOutbound } from '../../utils/messenger';

/* ─── Bot/Agent icon ─── */
const ChipIcon: React.FC = () => (
  <div className="w-8 h-8 rounded-full bg-[#f0f4f8] flex items-center justify-center border border-[#e5e7eb] flex-shrink-0">
    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="text-[#0f6885]">
      <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" />
      <line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" />
      <line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
    </svg>
  </div>
);

/* ─── User icon ─── */
const UserIcon: React.FC = () => (
  <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  </div>
);

interface MsgBubbleProps {
  msg: Message;
}

const MsgBubble: React.FC<MsgBubbleProps> = ({ msg }) => {
  const out = isOutbound(msg);
  const rawTs = msg.created_at || msg.timestamp || msg.sent_at;
  const time = rawTs
    ? new Date(rawTs).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
    : '';
  const text = msg.text || msg.content || msg.message_text || msg.body || '';

  if (out) {
    return (
      <div className="flex justify-end items-end gap-3 mb-6">
        <div className="flex flex-col items-end gap-1 max-w-[65%]">
          <div className="bg-[#0f6885] text-white rounded-2xl rounded-br-sm shadow-sm px-5 py-3">
            <span className="text-[15px] leading-relaxed break-words whitespace-pre-wrap">{text || <em className="opacity-60">message vide</em>}</span>
            {msg.confidence_score !== undefined && (
              <span className="mt-2 inline-block bg-white/20 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-widest">
                Score: {msg.confidence_score}
              </span>
            )}
            {msg.fallback_triggered && (
              <span className="mt-1 ml-1 inline-flex items-center gap-1 bg-amber-400/30 text-amber-100 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-widest">
                <AlertCircle className="w-3 h-3" /> Fallback
              </span>
            )}
          </div>
          <span className="text-[11px] text-gray-400 mr-1">{time}</span>
        </div>
        <ChipIcon />
      </div>
    );
  }

  // Detect image URL
  const imageUrl = text ? text.match(/https?:\/\/[^\s\][\\"'<>)]+/i)?.[0] : null;
  const pureText = imageUrl ? text.replace(imageUrl, '').replace(/^\s*[\][]?\s*\[Image[^\]]*\]?/i, '').trim() : text;

  return (
    <div className="flex items-end gap-3 mb-6">
      <UserIcon />
      <div className="flex flex-col gap-1 max-w-[65%]">
        <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm overflow-hidden">
          {imageUrl && (
            <>
              <img src={imageUrl} alt="media" crossOrigin="anonymous"
                className="w-full max-h-72 object-cover"
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
              <a href={imageUrl} target="_blank" rel="noopener noreferrer"
                className="block px-4 py-2 text-[11px] text-[#0f6885] hover:underline truncate">
                🔗 Voir l'image
              </a>
            </>
          )}
          {pureText && (
            <p className="text-gray-800 text-[15px] leading-relaxed break-words whitespace-pre-wrap px-5 py-3">{pureText}</p>
          )}
        </div>
        <span className="text-[11px] text-gray-400 ml-1">{time}</span>
      </div>
    </div>
  );
};

export default MsgBubble;
