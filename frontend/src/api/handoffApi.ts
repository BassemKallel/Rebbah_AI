/**
 * handoffApi.ts — Human Handoff API client
 *
 * Provides typed wrappers for all human handoff endpoints.
 * Uses the shared JWT axiosInstance.
 */
import api from './axiosInstance';

const CRM = '/api/v1/crm';

// ─── Per-conversation handoff ──────────────────────────────────────────────────

/** Agent prend le relais sur une conversation (bot mis en pause). */
export const takeoverConversation = (conversationId: number) =>
  api.post(`${CRM}/conversations/${conversationId}/takeover/`);

/** Remettre la conversation au bot. */
export const releaseConversation = (conversationId: number) =>
  api.post(`${CRM}/conversations/${conversationId}/release/`);

/** Agent envoie un message directement (via Meta Messenger). */
export const agentReply = (conversationId: number, text: string) =>
  api.post(`${CRM}/conversations/${conversationId}/agent-reply/`, { text });

/** Récupérer le statut de handoff d'une conversation. */
export const fetchHandoffStatus = (conversationId: number) =>
  api.get(`${CRM}/conversations/${conversationId}/handoff-status/`);

// ─── Global bot toggle ─────────────────────────────────────────────────────────

/** Activer ou désactiver le bot globalement pour une boutique. */
export const toggleBot = (shopId: string, botEnabled: boolean) =>
  api.patch(`${CRM}/bot-configurations/${shopId}/toggle-bot/`, { bot_enabled: botEnabled });
