import type { Message, Conversation } from '../types';

/**
 * Determine if a message is from the bot/agent side.
 */
export const isOutbound = (msg: Message): boolean => {
  const sender = (msg.sender || msg.sender_type || msg.direction || '').toUpperCase();
  return sender === 'BOT' || sender === 'AGENT' || sender === 'OUTBOUND';
};

/**
 * Resolve the display name of a conversation.
 */
export const getConversationName = (conv: Conversation): string =>
  conv.lead_details?.name ||
  conv.sender_name ||
  conv.user_name ||
  conv.sender_id ||
  `Conversation #${conv.id}`;

/**
 * Get the PSID key from a conversation (used for grouping).
 */
export const getConversationPsid = (conv: Conversation): string =>
  conv.lead_details?.platform_id ||
  conv.sender_id ||
  conv.user_id ||
  String(conv.id);
