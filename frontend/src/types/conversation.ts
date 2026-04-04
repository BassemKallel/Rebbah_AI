export interface LeadDetails {
  platform_id: string;
  name: string;
}

export interface Conversation {
  id: number;
  lead: number;
  lead_details: LeadDetails | null;
  shop_id: string;
  state: string;
  context_data: Record<string, unknown>;
  missing_entities: string[];
  sender_id?: string;
  sender_name?: string;
  user_id?: string;
  user_name?: string;
  last_message?: string;
  last_message_text?: string;
  snippet?: string;
  unread_count?: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  /** Internal grouping field — PSID key */
  _psid?: string;
  /** Internal grouping field — all conversation IDs for this PSID */
  _convIds?: number[];
}

export interface Message {
  id: number;
  conversation: number;
  sender: 'USER' | 'BOT' | 'AGENT';
  sender_type?: string;
  direction?: string;
  text: string;
  content?: string;
  message_text?: string;
  body?: string;
  extracted_intent: string | null;
  intent_confidence_score: number | null;
  extracted_entities: Record<string, unknown> | null;
  is_fallback: boolean;
  confidence_score?: number;
  fallback_triggered?: boolean;
  conversation_state_before: string;
  conversation_state_after: string;
  created_at: string;
  timestamp?: string;
  sent_at?: string;
  mid?: string;
}
