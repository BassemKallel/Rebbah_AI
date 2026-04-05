import axios from 'axios';
import { getAccessToken } from '../providers/AuthProvider';

const crm = axios.create({
  baseURL: process.env.REACT_APP_CRM_API_URL || 'http://localhost:8000/api/v1/crm',
  headers: { 'Content-Type': 'application/json' },
});

// Dynamic auth: inject JWT token on every request
crm.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-redirect to login on 401
crm.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

/**
 * Fetch paginated list of conversations.
 * @param {string} [shopId] - Optional shop filter
 */
export const fetchConversations = (shopId?: string) =>
  crm.get('/conversations/', { params: shopId ? { shop_id: shopId } : {} });

/**
 * Fetch message history for a given conversation.
 * @param {number} conversationId
 * @param {number} [page]
 */
export const fetchMessages = (conversationId: number, page?: number) =>
  crm.get(`/conversations/${conversationId}/messages/`, {
    params: page ? { page } : {},
  });

/**
 * Send a message as AGENT in a conversation.
 * @param {number} conversationId
 * @param {string} text
 */
export const sendMessage = (conversationId: number, text: string) =>
  crm.post(`/conversations/${conversationId}/messages/`, { text, sender: 'AGENT' });

// ─── Leads ───────────────────────────────────────────────────────────────────

/** List leads, optionally filtered by shop. */
export const fetchLeads = (shopId?: string) =>
  crm.get('/leads/', { params: shopId ? { shop_id: shopId } : {} });

/** Get a single lead by id. */
export const fetchLead = (id: number) =>
  crm.get(`/leads/${id}/`);

/** Create a new lead. */
export const createLead = (payload: Record<string, unknown>) =>
  crm.post('/leads/', payload);

/** Partial update of a lead (address, phone_number, has_pending_order…). */
export const patchLead = (id: number, patch: Record<string, unknown>) =>
  crm.patch(`/leads/${id}/`, patch);

/** Full replacement update of a lead. */
export const updateLead = (id: number, payload: Record<string, unknown>) =>
  crm.put(`/leads/${id}/`, payload);

/** Delete a lead. */
export const deleteLead = (id: number) =>
  crm.delete(`/leads/${id}/`);
