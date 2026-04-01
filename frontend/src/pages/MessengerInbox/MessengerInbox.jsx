import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Loader, Send, AlertCircle, MessageCircle } from 'lucide-react';
import MainLayout from '../../components/layout/MainLayout';
import MessengerSidebar from './MessengerSidebar';
import { fetchConversations, fetchMessages } from '../../api/crmApi';

// ─── Bubble sub-components ───────────────────────────────────────────────────

const ChipIcon = () => (
    <div className="w-8 h-8 rounded-full bg-[#f0f4f8] flex items-center justify-center border border-[#e5e7eb] flex-shrink-0">
        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" className="text-[#0f6885]">
            <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
            <rect x="9" y="9" width="6" height="6"></rect>
            <line x1="9" y1="1" x2="9" y2="4"></line>
            <line x1="15" y1="1" x2="15" y2="4"></line>
            <line x1="9" y1="20" x2="9" y2="23"></line>
            <line x1="15" y1="20" x2="15" y2="23"></line>
            <line x1="20" y1="9" x2="23" y2="9"></line>
            <line x1="20" y1="14" x2="23" y2="14"></line>
            <line x1="1" y1="9" x2="4" y2="9"></line>
            <line x1="1" y1="14" x2="4" y2="14"></line>
        </svg>
    </div>
);

/**
 * Determine if a message is from the bot/agent side.
 * The POC may use 'BOT', 'AGENT', 'bot', 'agent', or a direction field.
 */
const isOutbound = (msg) => {
    const sender = (msg.sender || msg.sender_type || msg.direction || '').toUpperCase();
    return sender === 'BOT' || sender === 'AGENT' || sender === 'OUTBOUND';
};

const MsgBubble = ({ msg, leadName }) => {
    const out = isOutbound(msg);
    const rawTs = msg.created_at || msg.timestamp || msg.sent_at;
    const time = rawTs
        ? new Date(rawTs).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
        : '';
    const text = msg.text || msg.content || msg.message_text || msg.body || '';

    if (out) {
        // BOT / AGENT → droite, bulle bleue
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

    // Detect any URL — strip trailing brackets/punctuation added by Facebook webhook format
    const imageUrl = text ? text.match(/https?:\/\/[^\s\][\\"'<>)]+/i)?.[0] : null;
    const pureText = imageUrl ? text.replace(imageUrl, '').replace(/^\s*[\][]?\s*\[Image[^\]]*\]?/i, '').trim() : text;

    return (
        <div className="flex items-end gap-3 mb-6">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                </svg>
            </div>
            <div className="flex flex-col gap-1 max-w-[65%]">
                <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm overflow-hidden">
                    {imageUrl && (
                        <>
                            <img
                                src={imageUrl}
                                alt="media"
                                crossOrigin="anonymous"
                                className="w-full max-h-72 object-cover"
                                onError={(e) => { e.target.style.display = 'none'; }}
                            />
                            <a
                                href={imageUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block px-4 py-2 text-[11px] text-[#0f6885] hover:underline truncate"
                            >
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

// ─── Main Page ───────────────────────────────────────────────────────────────

const SHOP_ID = process.env.REACT_APP_SHOP_ID || '';

const MessengerInbox = () => {
    const [conversations, setConversations] = useState([]);
    const [convsLoading, setConvsLoading] = useState(true);
    const [convsError, setConvsError] = useState(null);

    const [selected, setSelected] = useState(null);
    const [messages, setMessages] = useState([]);
    const [msgsLoading, setMsgsLoading] = useState(false);

    const [search, setSearch] = useState('');
    const [draft, setDraft] = useState('');
    const [lastMessages, setLastMessages] = useState({});  // { psid: lastMsgText }
    const messagesEndRef = useRef(null);

    // ── Load conversations ──────────────────────────────────────────────────────
    const loadConversations = useCallback(async () => {
        setConvsLoading(true);
        setConvsError(null);
        try {
            const { data } = await fetchConversations(SHOP_ID);
            // Handle both paginated DRF { results: [] } and plain array
            setConversations(Array.isArray(data) ? data : (data.results ?? []));
        } catch (err) {
            setConvsError(
                err?.response?.data?.detail ||
                err?.message ||
                'Impossible de charger les conversations.'
            );
        } finally {
            setConvsLoading(false);
        }
    }, []);

    useEffect(() => { loadConversations(); }, [loadConversations]);

    // ── Load messages (all convs sharing the same PSID) ────────────────────────
    const loadMessages = useCallback(async (convIds) => {
        setMsgsLoading(true);
        setMessages([]);
        try {
            const ids = Array.isArray(convIds) ? convIds : [convIds];
            const results = await Promise.all(ids.map((id) => fetchMessages(id)));
            const all = results.flatMap(({ data }) =>
                Array.isArray(data) ? data : (data.results ?? [])
            );
            // Sort chronologically and remove exact duplicates by id
            const seen = new Set();
            const merged = all
                .filter((m) => {
                    const key = m.id ?? `${m.created_at}-${m.text}`;
                    if (seen.has(key)) return false;
                    seen.add(key);
                    return true;
                })
                .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
            setMessages(merged);
        } catch (_) {
            setMessages([]);
        } finally {
            setMsgsLoading(false);
        }
    }, []);

    const handleSelect = (conv) => {
        setSelected(conv);
        setDraft('');
        loadMessages(conv._convIds ?? [conv.id]);
    };

    // Auto-scroll on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, msgsLoading]);

    // ── Group conversations by PSID (same Messenger user = one entry) ───────────
    const grouped = useMemo(() => {
        const map = new Map();
        conversations.forEach((conv) => {
            const psid =
                conv.lead_details?.platform_id ||
                conv.sender_id ||
                conv.user_id ||
                String(conv.id);
            if (!map.has(psid)) {
                map.set(psid, { ...conv, _psid: psid, _convIds: [conv.id] });
            } else {
                const existing = map.get(psid);
                existing._convIds.push(conv.id);
                // Keep most recent conv's metadata for display
                if (new Date(conv.updated_at) > new Date(existing.updated_at)) {
                    map.set(psid, { ...conv, _psid: psid, _convIds: existing._convIds });
                }
            }
        });
        return Array.from(map.values()).sort(
            (a, b) => new Date(b.updated_at) - new Date(a.updated_at)
        );
    }, [conversations]);

    // ── Fetch last message for each grouped conversation (for sidebar preview) ───
    useEffect(() => {
        if (grouped.length === 0) return;
        let cancelled = false;
        (async () => {
            const results = await Promise.allSettled(
                grouped.map((conv) =>
                    fetchMessages(conv.id).then(({ data }) => {
                        const msgs = Array.isArray(data) ? data : (data.results ?? []);
                        const last = msgs[msgs.length - 1];
                        const text = last ? (last.text || last.content || last.body || '') : null;
                        return { psid: conv._psid ?? String(conv.id), text };
                    })
                )
            );
            if (cancelled) return;
            const map = {};
            results.forEach((r) => {
                if (r.status === 'fulfilled' && r.value.text) {
                    map[r.value.psid] = r.value.text;
                }
            });
            setLastMessages(map);
        })();
        return () => { cancelled = true; };
    }, [grouped]);

    // ── Search filter (on grouped list) ─────────────────────────────────────────
    const filtered = grouped.filter((c) => {
        const lead = c.lead_details || {};
        const name = lead.name || c.sender_name || c.user_name || c._psid || '';
        return (
            name.toLowerCase().includes(search.toLowerCase()) ||
            c._convIds.some((id) => String(id).includes(search))
        );
    });

    // ── Resolve display name of selected conv ───────────────────────────────────
    const selectedName = selected
        ? (selected.lead_details?.name ||
            selected.sender_name ||
            selected.user_name ||
            selected.sender_id ||
            `Conversation #${selected.id}`)
        : '';

    // ── Sidebar ─────────────────────────────────────────────────────────────────
    const sidebarContent = (
        <MessengerSidebar
            conversations={filtered}
            selected={selected}
            onSelect={handleSelect}
            search={search}
            setSearch={setSearch}
            loading={convsLoading}
            lastMessages={lastMessages}
        />
    );

    return (
        <MainLayout secondarySidebar={sidebarContent}>
            {convsError && (
                <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded-xl shadow flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {convsError}
                </div>
            )}

            {selected ? (
                <div className="flex-1 flex flex-col h-full bg-[#f8fafc]">

                    {/* Chat header */}
                    <div className="px-8 py-4 bg-white border-b border-gray-100 flex items-center gap-3 shrink-0">
                        <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#9ca3af" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                                <circle cx="12" cy="7" r="4" />
                            </svg>
                        </div>
                        <div>
                            <p className="font-bold text-[#1f2937] text-sm">{selectedName}</p>
                            <p className="text-xs text-gray-400 flex items-center gap-1">
                                <MessageCircle className="w-3 h-3" /> Messenger
                            </p>
                        </div>
                        <button
                            onClick={() => loadMessages(selected.id)}
                            className="ml-auto text-xs text-[#0f6885] hover:underline"
                        >
                            Rafraîchir
                        </button>
                    </div>

                    {/* Messages area */}
                    <div className="flex-1 overflow-y-auto px-8 py-8 relative">
                        {msgsLoading ? (
                            <div className="flex justify-center py-10">
                                <Loader className="w-8 h-8 animate-spin text-[#0f6885]" />
                            </div>
                        ) : messages.length === 0 ? (
                            <p className="text-center text-gray-400 text-sm py-10">
                                Aucun message dans cette conversation.
                            </p>
                        ) : (
                            messages.map((msg) => <MsgBubble key={msg.id ?? msg.mid ?? Math.random()} msg={msg} leadName={selectedName} />)
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input bar (read-only for POC; send via existing sendPocMessage if needed) */}
                    <div className="p-6 bg-[#f8fafc] border-t border-transparent shrink-0 flex justify-center pb-8">
                        <div className="bg-white border border-gray-200 rounded-[28px] w-[95%] shadow-sm px-4 py-3 flex items-center gap-3 transition-all focus-within:ring-2 focus-within:ring-[#0f6885]/20 focus-within:border-[#0f6885]">
                            <input
                                value={draft}
                                onChange={(e) => setDraft(e.target.value)}
                                placeholder="Répondre à ce client…"
                                className="flex-1 bg-transparent text-[15px] font-medium placeholder-gray-400 text-gray-800 outline-none"
                            />
                            <button
                                disabled={!draft.trim()}
                                className="bg-[#0f6885] hover:bg-[#0c5973] transition-colors rounded-full flex items-center gap-2 px-5 py-2.5 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <span className="font-semibold text-sm">Envoyer</span>
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            ) : (
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
            )}
        </MainLayout>
    );
};

export default MessengerInbox;
