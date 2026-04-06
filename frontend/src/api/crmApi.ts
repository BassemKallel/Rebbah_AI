import api from './axiosInstance';

// ─── Conversations ──────────────────────────────────────────────────────────

/** Fetch paginated list of conversations. */
export const fetchConversations = (shopId?: string) =>
  api.get('/api/v1/crm/conversations/', { params: shopId ? { shop_id: shopId } : {} });

/** Fetch message history for a given conversation. */
export const fetchMessages = (conversationId: number, page?: number) =>
  api.get(`/api/v1/crm/conversations/${conversationId}/messages/`, {
    params: page ? { page } : {},
  });

/** Send a message as AGENT in a conversation. */
export const sendMessage = (conversationId: number, text: string) =>
  api.post(`/api/v1/crm/conversations/${conversationId}/messages/`, { text, sender: 'AGENT' });

// ─── Leads ───────────────────────────────────────────────────────────────────

/** List leads, optionally filtered by shop. */
export const fetchLeads = (shopId?: string) =>
  api.get('/api/v1/crm/leads/', { params: shopId ? { shop_id: shopId } : {} });

/** Get a single lead by id. */
export const fetchLead = (id: number) =>
  api.get(`/api/v1/crm/leads/${id}/`);

/** Create a new lead. */
export const createLead = (payload: Record<string, unknown>) =>
  api.post('/api/v1/crm/leads/', payload);

/** Partial update of a lead. */
export const patchLead = (id: number, patch: Record<string, unknown>) =>
  api.patch(`/api/v1/crm/leads/${id}/`, patch);

/** Full replacement update of a lead. */
export const updateLead = (id: number, payload: Record<string, unknown>) =>
  api.put(`/api/v1/crm/leads/${id}/`, payload);

/** Delete a lead. */
export const deleteLead = (id: number) =>
  api.delete(`/api/v1/crm/leads/${id}/`);
