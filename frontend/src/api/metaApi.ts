import axios from 'axios';

const BASE = process.env.REACT_APP_META_API_URL || 'http://localhost:8000/api/v1/gateway/messenger/poc';

const pocClient = axios.create({ baseURL: BASE });

// ─── GET helpers ────────────────────────────────────────────────────────────

/**
 * List Messenger conversations for a shop.
 * GET /poc/conversations/?shop_id=…
 * @param {string} shopId
 */
export const fetchPocConversations = (shopId) =>
  pocClient.get('/conversations/', { params: shopId ? { shop_id: shopId } : {} });

/**
 * Fetch messages for a given Messenger conversation.
 * GET /poc/conversations/{id}/messages/
 * @param {string|number} conversationId
 */
export const fetchPocMessages = (conversationId) =>
  pocClient.get(`/conversations/${conversationId}/messages/`);

// ─── POST helper ─────────────────────────────────────────────────────────────

/**
 * Send a message via the Messenger POC gateway.
 * - Text only  → JSON  { user_id, shop_id, text }
 * - With file  → multipart/form-data  (image attached as "image")
 * @param {{ user_id: string, shop_id: string, text?: string, imageFile?: File }} payload
 */
export const sendPocMessage = ({ user_id, shop_id, text, imageFile }) => {
  if (imageFile) {
    const form = new FormData();
    form.append('user_id', user_id);
    form.append('shop_id', shop_id);
    if (text) form.append('text', text);
    form.append('image', imageFile);
    return pocClient.post('', form);
  }
  return pocClient.post('', { user_id, shop_id, text }, {
    headers: { 'Content-Type': 'application/json' },
  });
};
