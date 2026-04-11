import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Loader, AlertCircle, UserCheck } from 'lucide-react';
import MainLayout from '../../components/layout/MainLayout';
import MessengerSidebar from './MessengerSidebar';
import MsgBubble from '../../components/messenger/MsgBubble';
import ChatHeader from '../../components/messenger/ChatHeader';
import ChatInput from '../../components/messenger/ChatInput';
import EmptyState from '../../components/messenger/EmptyState';
import { fetchConversations, fetchMessages } from '../../api/crmApi';
import { takeoverConversation, releaseConversation, agentReply } from '../../api/handoffApi';
import { SHOP_ID } from '../../constants';
import { getConversationName, getConversationPsid } from '../../utils/messenger';
import type { Conversation, Message } from '../../types';

const MessengerInbox: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [convsLoading, setConvsLoading] = useState(true);
  const [convsError, setConvsError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [msgsLoading, setMsgsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState('');
  const [lastMessages, setLastMessages] = useState<Record<string, string>>({});
  const [handoffLoading, setHandoffLoading] = useState(false);

  /**
   * Mobile: 'list' = show conversation list, 'chat' = show chat.
   * On md+ both are always visible (sidebar + main).
   */
  const [mobileView, setMobileView] = useState<'list' | 'chat'>('list');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* ── Load conversations ── */
  const loadConversations = useCallback(async () => {
    setConvsLoading(true);
    setConvsError(null);
    try {
      const { data } = await fetchConversations(SHOP_ID);
      setConversations(Array.isArray(data) ? data : (data.results ?? []));
    } catch (err: any) {
      setConvsError(err?.response?.data?.detail || err?.message || 'Impossible de charger les conversations.');
    } finally {
      setConvsLoading(false);
    }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  /* ── Load messages ── */
  const loadMessages = useCallback(async (convIds: number[]) => {
    setMsgsLoading(true);
    setMessages([]);
    try {
      const ids = Array.isArray(convIds) ? convIds : [convIds];
      const results = await Promise.all(ids.map((id) => fetchMessages(id)));
      const all = results.flatMap(({ data }) => Array.isArray(data) ? data : (data.results ?? []));
      const seen = new Set<string | number>();
      const merged = all
        .filter((m) => {
          const key = m.id ?? `${m.created_at}-${m.text}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      setMessages(merged);
    } catch { setMessages([]); }
    finally { setMsgsLoading(false); }
  }, []);

  const handleSelect = (conv: Conversation) => {
    setSelected(conv);
    setDraft('');
    loadMessages(conv._convIds ?? [conv.id]);
    setMobileView('chat'); // switch to chat on mobile
  };

  const handleBackToList = () => {
    setMobileView('list');
    setSelected(null);
  };

  /* ── Human Handoff handlers ── */
  const handleTakeover = useCallback(async () => {
    if (!selected) return;
    setHandoffLoading(true);
    try {
      await takeoverConversation(selected.id);
      // Optimistic update
      setSelected(prev => prev ? { ...prev, is_human_controlled: true } : prev);
      setConversations(prev =>
        prev.map(c => c.id === selected.id ? { ...c, is_human_controlled: true } : c)
      );
    } catch (err) {
      console.error('[HANDOFF] Takeover failed:', err);
    } finally {
      setHandoffLoading(false);
    }
  }, [selected]);

  const handleRelease = useCallback(async () => {
    if (!selected) return;
    setHandoffLoading(true);
    try {
      await releaseConversation(selected.id);
      setSelected(prev => prev ? { ...prev, is_human_controlled: false, human_agent_name: null } : prev);
      setConversations(prev =>
        prev.map(c => c.id === selected.id ? { ...c, is_human_controlled: false } : c)
      );
    } catch (err) {
      console.error('[HANDOFF] Release failed:', err);
    } finally {
      setHandoffLoading(false);
    }
  }, [selected]);

  const handleSend = useCallback(async () => {
    if (!selected || !draft.trim()) return;
    const text = draft.trim();
    setDraft('');
    try {
      await agentReply(selected.id, text);
      // Reload messages to show the sent message
      loadMessages(selected._convIds ?? [selected.id]);
    } catch (err) {
      console.error('[HANDOFF] Agent reply failed:', err);
    }
  }, [selected, draft]);

  /* ── Real-time polling when in human mode ── */
  useEffect(() => {
    if (!selected?.is_human_controlled) return;
    const interval = setInterval(() => {
      loadMessages(selected._convIds ?? [selected.id]);
    }, 5000);
    return () => clearInterval(interval);
  }, [selected?.is_human_controlled, selected?.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, msgsLoading]);

  /* ── Group conversations by PSID ── */
  const grouped = useMemo(() => {
    const map = new Map<string, Conversation>();
    conversations.forEach((conv) => {
      const psid = getConversationPsid(conv);
      if (!map.has(psid)) {
        map.set(psid, { ...conv, _psid: psid, _convIds: [conv.id] });
      } else {
        const existing = map.get(psid)!;
        existing._convIds!.push(conv.id);
        if (new Date(conv.updated_at) > new Date(existing.updated_at)) {
          map.set(psid, { ...conv, _psid: psid, _convIds: existing._convIds });
        }
      }
    });
    return Array.from(map.values()).sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  }, [conversations]);

  /* ── Fetch last message per conversation ── */
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
      const map: Record<string, string> = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled' && r.value.text) map[r.value.psid] = r.value.text;
      });
      setLastMessages(map);
    })();
    return () => { cancelled = true; };
  }, [grouped]);

  /* ── Filtered ── */
  const filtered = grouped.filter((c) => {
    const name = getConversationName(c);
    return (
      name.toLowerCase().includes(search.toLowerCase()) ||
      c._convIds?.some((id) => String(id).includes(search))
    );
  });

  const selectedName = selected ? getConversationName(selected) : '';

  /* ── Chat panel content ── */
  const ChatPanel = () => (
    <div className="flex-1 flex flex-col h-full bg-[#f8fafc]">
      <ChatHeader
        name={selectedName}
        onRefresh={() => loadMessages(selected!._convIds ?? [selected!.id])}
        onBack={handleBackToList}
        isHumanControlled={selected?.is_human_controlled ?? false}
        humanAgentName={selected?.human_agent_name}
        onTakeover={handleTakeover}
        onRelease={handleRelease}
      />

      {/* Handoff banner */}
      {selected?.is_human_controlled && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center gap-2 text-amber-700 text-xs font-medium">
          <UserCheck className="w-4 h-4 flex-shrink-0" />
          <span>Vous gérez cette conversation directement. Le bot est en pause.</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-4 md:py-8 scrollbar-thin">
        {msgsLoading ? (
          <div className="flex justify-center py-10">
            <Loader className="w-8 h-8 animate-spin text-[#0f6885]" />
          </div>
        ) : messages.length === 0 ? (
          <p className="text-center text-gray-400 text-sm py-10">
            Aucun message dans cette conversation.
          </p>
        ) : (
          messages.map((msg) => (
            <MsgBubble key={msg.id ?? msg.mid ?? Math.random()} msg={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput
        draft={draft}
        onDraftChange={setDraft}
        onSend={handleSend}
        isHumanControlled={selected?.is_human_controlled ?? false}
      />
    </div>
  );

  /* ── Conversation list panel (for mobile content area) ── */
  const ListPanel = () => (
    <div className="flex-1 overflow-hidden">
      <MessengerSidebar
        conversations={filtered}
        selected={selected}
        onSelect={handleSelect}
        search={search}
        setSearch={setSearch}
        loading={convsLoading}
        lastMessages={lastMessages}
      />
    </div>
  );

  /* ── Sidebar for desktop (md+) ── */
  const desktopSidebar = (
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
    <MainLayout secondarySidebar={desktopSidebar}>
      {/* Error banner */}
      {convsError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2 rounded-xl shadow flex items-center gap-2 w-[90%] max-w-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />{convsError}
        </div>
      )}

      {/*
        On mobile (<md):
          - secondarySidebar is HIDDEN by MainLayout (fix #1)
          - We show either the list OR the chat inside the content area
        On desktop (md+):
          - secondarySidebar (conversation list) is always visible
          - Content area shows the chat or empty state
      */}

      {/* ── Mobile: list view ── */}
      <div className={`md:hidden h-full flex flex-col ${mobileView === 'list' ? 'block' : 'hidden'}`}>
        <ListPanel />
      </div>

      {/* ── Mobile: chat view ── */}
      {mobileView === 'chat' && selected && (
        <div className="md:hidden h-full flex flex-col animate-slide-in-right">
          <ChatPanel />
        </div>
      )}

      {/* ── Desktop: always show chat (or empty state) ── */}
      {selected ? (
        <div className="hidden md:flex flex-1 flex-col h-full">
          <ChatPanel />
        </div>
      ) : (
        <div className="hidden md:flex flex-1 flex-col h-full">
          <EmptyState />
        </div>
      )}
    </MainLayout>
  );
};

export default MessengerInbox;
