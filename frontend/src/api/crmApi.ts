/**
 * crmApi.ts — CRM API client using the shared JWT axiosInstance.
 *
 * Uses axiosInstance (with JWT interceptor) instead of its own axios.create().
 * The JWT token is automatically injected from localStorage on every request.
 */
import api from './axiosInstance';

const CRM = '/api/v1/crm';

// ─── Conversations ────────────────────────────────────────────────────────────

/** Fetch paginated list of conversations, optionally filtered by shop. */
export const fetchConversations = (shopId?: string) =>
  api.get(`${CRM}/conversations/`, { params: shopId ? { shop_id: shopId } : {} });

/** Fetch message history for a given conversation. */
export const fetchMessages = (conversationId: number, page?: number) =>
  api.get(`${CRM}/conversations/${conversationId}/messages/`, {
    params: page ? { page } : {},
  });

/** Send a message as AGENT in a conversation. */
export const sendMessage = (conversationId: number, text: string) =>
  api.post(`${CRM}/conversations/${conversationId}/messages/`, {
    text,
    sender: 'AGENT',
  });

// ─── Leads ───────────────────────────────────────────────────────────────────

/** List leads, optionally filtered by shop. */
export const fetchLeads = (shopId?: string) =>
  api.get(`${CRM}/leads/`, { params: shopId ? { shop_id: shopId } : {} });

/** Get a single lead by id. */
export const fetchLead = (id: number) =>
  api.get(`${CRM}/leads/${id}/`);

/** Create a new lead. */
export const createLead = (payload: Record<string, unknown>) =>
  api.post(`${CRM}/leads/`, payload);

/** Partial update of a lead. */
export const patchLead = (id: number, patch: Record<string, unknown>) =>
  api.patch(`${CRM}/leads/${id}/`, patch);

/** Full replacement update of a lead. */
export const updateLead = (id: number, payload: Record<string, unknown>) =>
  api.put(`${CRM}/leads/${id}/`, payload);

/** Delete a lead. */
export const deleteLead = (id: number) =>
  api.delete(`${CRM}/leads/${id}/`);

// ─── Catalog (Visual RAG) ────────────────────────────────────────────────────

export const fetchCatalog = (shopId?: string) =>
  api.get(`${CRM}/catalog/`, { params: shopId ? { shop_id: shopId } : {} });

export const deleteCatalogItem = (id: number) =>
  api.delete(`${CRM}/catalog/${id}/`);

export const uploadCatalogItem = (formData: FormData) =>
  api.post('/api/v1/gateway/catalog/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const updateCatalogMetadata = (payload: { shop_id: string; item_id: string; metadata: Record<string, unknown> }) =>
  api.patch('/api/v1/gateway/catalog/update-metadata', payload);

export const importCatalogCsv = (formData: FormData) =>
  api.post('/api/v1/gateway/catalog/import-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
