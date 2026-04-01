import React, { useState, useRef, useEffect } from 'react';
import {
  Send, Paperclip, Smile, ChevronDown,
  ShoppingBag, CheckCheck, Wifi, WifiOff
} from 'lucide-react';

/* ─────────────────────────── Mock store info ──────────────────────── */
const STORE = {
  name: 'TikTak Store',
  tagline: 'Votre boutique de mode en Tunisie 🇹🇳',
  avatar: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=150&q=80',
  responseTime: 'Répond généralement en quelques minutes',
  status: 'online',
};

/* ─────────────────────────── Bot auto-replies ─────────────────────── */
const BOT_REPLIES = [
  "Bonjour ! Merci de nous avoir contactés. Comment puis-je vous aider aujourd'hui ?",
  "Bien reçu ! Notre équipe va traiter votre demande très rapidement.",
  "Merci pour votre message. Nous vous répondrons dans les plus brefs délais.",
  "Parfait ! Avez-vous d'autres questions ?",
];

let botReplyIndex = 0;
const getNextBotReply = () => {
  const reply = BOT_REPLIES[botReplyIndex % BOT_REPLIES.length];
  botReplyIndex++;
  return reply;
};

/* ─────────────────────────── Typing indicator ─────────────────────── */
const TypingIndicator = () => (
  <div className="flex items-end gap-2 mb-4">
    <img src={STORE.avatar} alt={STORE.name} className="w-8 h-8 rounded-full object-cover flex-shrink-0" />
    <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
      <div className="flex items-center gap-1">
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  </div>
);

/* ─────────────────────────── Main Component ─────────────────────────── */
const ClientChat = () => {
  const now = new Date();
  const initTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'store',
      text: `Bonjour ! 👋 Bienvenue chez ${STORE.name}. Comment pouvons-nous vous aider aujourd'hui ?`,
      time: initTime,
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isConnected] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!isMinimized) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping, isMinimized]);

  const getTime = () => {
    const d = new Date();
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  };

  const handleSend = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const userMsg = { id: Date.now(), sender: 'client', text, time: getTime() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    inputRef.current?.focus();

    // Simulate store typing then responding
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      const storeMsg = {
        id: Date.now() + 1,
        sender: 'store',
        text: getNextBotReply(),
        time: getTime(),
      };
      setMessages((prev) => [...prev, storeMsg]);
    }, 1500 + Math.random() * 1000);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  /* Quick-reply suggestions */
  const suggestions = [
    'Voir les produits',
    'Délai de livraison ?',
    'Comment commander ?',
    'Vos promotions',
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#d6ecf3] via-[#eaf4f8] to-[#f0f7fb] flex items-center justify-center p-4">

      {/* Widget Shell */}
      <div className="w-full max-w-[420px] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col transition-all duration-300"
        style={{ height: isMinimized ? 'auto' : '680px' }}>

        {/* ── Header ── */}
        <div className="bg-[#0f6885] px-5 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <img
                  src={STORE.avatar}
                  alt={STORE.name}
                  className="w-12 h-12 rounded-full object-cover border-2 border-white/30"
                />
                <span className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[#0f6885] ${STORE.status === 'online' ? 'bg-emerald-400' : 'bg-gray-400'}`} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-white font-bold text-base">{STORE.name}</p>
                  <ShoppingBag className="w-4 h-4 text-white/60" />
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  {isConnected
                    ? <Wifi className="w-3 h-3 text-emerald-300" />
                    : <WifiOff className="w-3 h-3 text-red-300" />}
                  <p className="text-white/70 text-[11px] font-medium">{STORE.responseTime}</p>
                </div>
              </div>
            </div>
            <button
              onClick={() => setIsMinimized((v) => !v)}
              className="text-white/70 hover:text-white transition-colors p-1.5 hover:bg-white/10 rounded-lg"
            >
              <ChevronDown className={`w-5 h-5 transition-transform duration-300 ${isMinimized ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {/* Store tagline */}
          {!isMinimized && (
            <p className="text-white/60 text-xs mt-3 border-t border-white/10 pt-3">{STORE.tagline}</p>
          )}
        </div>

        {/* ── Body (hidden when minimized) ── */}
        {!isMinimized && (
          <>
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto px-5 py-5 space-y-1 bg-[#f7fbfd]">
              {messages.map((msg) => {
                const isClient = msg.sender === 'client';
                return (
                  <div key={msg.id} className={`flex w-full mb-3 items-end gap-2 ${isClient ? 'justify-end' : 'justify-start'}`}>
                    {/* Store avatar */}
                    {!isClient && (
                      <img src={STORE.avatar} alt={STORE.name} className="w-8 h-8 rounded-full object-cover flex-shrink-0 mb-1" />
                    )}

                    {/* Bubble */}
                    <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${isClient
                      ? 'bg-[#0f6885] text-white rounded-br-sm'
                      : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
                      }`}>
                      <p className="font-medium">{msg.text}</p>
                      <div className={`flex items-center justify-end gap-1 mt-1.5 ${isClient ? 'text-blue-100' : 'text-gray-400'}`}>
                        <span className="text-[10px]">{msg.time}</span>
                        {isClient && <CheckCheck className="w-3.5 h-3.5" />}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Typing indicator */}
              {isTyping && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {/* ── Quick replies ── */}
            {messages.length <= 2 && (
              <div className="px-4 py-2 bg-[#f7fbfd] border-t border-gray-100 flex gap-2 overflow-x-auto flex-shrink-0 scrollbar-hide">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      setInput(s);
                      inputRef.current?.focus();
                    }}
                    className="flex-shrink-0 text-xs font-semibold text-[#0f6885] border border-[#0f6885]/30 bg-[#eef6f9] hover:bg-[#0f6885] hover:text-white px-3 py-1.5 rounded-full transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {/* ── Input ── */}
            <div className="px-4 pb-5 pt-3 bg-white border-t border-gray-100 flex-shrink-0">
              <form
                onSubmit={handleSend}
                className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-2xl px-3 py-2.5 focus-within:ring-2 focus-within:ring-[#0f6885]/30 focus-within:border-[#0f6885] transition-all"
              >
                <button type="button" className="text-gray-400 hover:text-gray-600 transition-colors p-1">
                  <Paperclip className="w-4.5 h-4.5 -rotate-45" />
                </button>

                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Écrire un message..."
                  className="flex-1 bg-transparent text-sm text-gray-700 placeholder-gray-400 font-medium focus:outline-none"
                />

                <button type="button" className="text-gray-400 hover:text-gray-600 transition-colors p-1">
                  <Smile className="w-4.5 h-4.5" />
                </button>

                <button
                  type="submit"
                  disabled={!input.trim()}
                  className={`p-2 rounded-xl transition-all ${input.trim()
                    ? 'bg-[#0f6885] text-white hover:bg-[#0c5973] active:scale-95 shadow-sm'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    }`}
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>

              {/* Branding */}
              <p className="text-center text-[10px] text-gray-400 mt-2.5 font-medium">
                Propulsé par{' '}
                <span className="text-[#0f6885] font-bold">TikTak AI</span>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ClientChat;
