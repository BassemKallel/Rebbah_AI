import React from 'react';
import { Search, MessageCircle } from 'lucide-react';

const UserIcon = () => (
    <div className="w-11 h-11 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
        </svg>
    </div>
);

const MessengerSidebar = ({ conversations, selected, onSelect, search, setSearch, loading, lastMessages = {} }) => {
    return (
        <div className="h-full flex flex-col pt-5">
            {/* Header */}
            <div className="px-6 flex items-center gap-3 mb-5">
                <div className="w-8 h-8 rounded-full bg-[#0f6885]/10 flex items-center justify-center">
                    <MessageCircle className="w-4 h-4 text-[#0f6885]" />
                </div>
                <h2 className="text-xl font-extrabold text-[#1f2937]">Messenger</h2>
            </div>

            {/* Search */}
            <div className="px-6 mb-4">
                <div className="relative">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Rechercher une conversation…"
                        className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm
                       focus:outline-none focus:ring-2 focus:ring-[#0f6885]/30 focus:border-[#0f6885]
                       transition-colors placeholder-gray-400 text-gray-800 shadow-sm"
                    />
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto mt-1">
                {loading && (
                    <p className="text-center text-sm text-gray-400 py-8">Chargement…</p>
                )}
                {!loading && conversations.length === 0 && (
                    <p className="text-center text-sm text-gray-400 py-8">Aucune conversation</p>
                )}
                {conversations.map((conv) => {
                    const isSelected = selected?.id === conv.id;
                    // Support both DRF CRM shape (lead_details) and raw Messenger shape (sender_id / user_id)
                    const lead = conv.lead_details || {};
                    const name =
                        lead.name ||
                        conv.sender_name ||
                        conv.user_name ||
                        conv.sender_id ||
                        conv.user_id ||
                        `Conversation #${conv.id}`;

                    const psidKey = conv._psid ?? String(conv.id);
                    const preview =
                        lastMessages[psidKey] ||
                        conv.last_message ||
                        conv.last_message_text ||
                        conv.snippet ||
                        (conv.state ? `État : ${conv.state}` : '…');
                    const rawTime = conv.updated_at || conv.last_message_at || conv.created_at;
                    const time = rawTime
                        ? new Date(rawTime).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
                        : '';
                    const unread = conv.unread_count > 0 ? conv.unread_count : null;

                    return (
                        <button
                            key={conv.id}
                            onClick={() => onSelect(conv)}
                            className={`w-full flex items-center gap-3 px-6 py-3 text-left transition-colors relative border-l-4 ${isSelected
                                ? 'bg-gray-50/80 border-[#0f6885]'
                                : 'bg-transparent border-transparent hover:bg-gray-50'
                                }`}
                        >
                            <UserIcon />
                            <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-baseline mb-1">
                                    <span className="font-semibold text-sm text-gray-800 truncate pr-2">{name}</span>
                                    <span className="text-[10px] text-gray-400 font-medium flex-shrink-0">{time}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className={`text-xs truncate ${unread ? 'text-gray-800 font-semibold' : 'text-gray-500 font-medium'}`}>
                                        {preview}
                                    </span>
                                    {unread && (
                                        <span className="ml-2 flex-shrink-0 w-4 h-4 rounded-full bg-[#f97316] text-white flex items-center justify-center text-[9px] font-bold">
                                            {unread}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </button>
                    );
                })}

                {/* Hint when no conversation is selected */}
                {!loading && conversations.length > 0 && (
                    <p className="text-center text-[11px] text-gray-300 py-4 px-6">
                        ↑ Sélectionnez une conversation
                    </p>
                )}
            </div>
        </div>
    );
};

export default MessengerSidebar;
