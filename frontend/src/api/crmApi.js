import axios from 'axios';

const TOKEN = process.env.REACT_APP_SHOP_TOKEN || '';

const crm = axios.create({
  baseURL: process.env.REACT_APP_CRM_API_URL || 'http://localhost:8000/api/v1/crm',
  headers: {
    'Content-Type': 'application/json',
    ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
  },
});

/**
 * Fetch paginated list of conversations.
 * @param {string} [shopId] - Optional shop filter
 */
export const fetchConversations = (shopId) =>
  crm.get('/conversations/', { params: shopId ? { shop_id: shopId } : {} });

/**
 * Fetch message history for a given conversation.
 * @param {number} conversationId
 * @param {number} [page]
 */
export const fetchMessages = (conversationId, page) =>
  crm.get(`/conversations/${conversationId}/messages/`, {
    params: page ? { page } : {},
  });

/**
 * Send a message as AGENT in a conversation.
 * @param {number} conversationId
 * @param {string} text
 */
export const sendMessage = (conversationId, text) =>
  crm.post(`/conversations/${conversationId}/messages/`, { text, sender: 'AGENT' });

// ─── Leads ───────────────────────────────────────────────────────────────────

/** List leads, optionally filtered by shop. */
export const fetchLeads = (shopId) =>
  crm.get('/leads/', { params: shopId ? { shop_id: shopId } : {} });

/** Get a single lead by id. */
export const fetchLead = (id) =>
  crm.get(`/leads/${id}/`);

/** Create a new lead. */
export const createLead = (payload) =>
  crm.post('/leads/', payload);

/** Partial update of a lead (address, phone_number, has_pending_order…). */
export const patchLead = (id, patch) =>
  crm.patch(`/leads/${id}/`, patch);

/** Full replacement update of a lead. */
export const updateLead = (id, payload) =>
  crm.put(`/leads/${id}/`, payload);

/** Delete a lead. */
export const deleteLead = (id) =>
  crm.delete(`/leads/${id}/`);
