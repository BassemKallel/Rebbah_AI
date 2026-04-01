import axios from 'axios';

const API_BASE = process.env.REACT_APP_CRM_API_URL || 'http://localhost:8000/api/v1/crm';

const botConfigApi = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Get bot configuration for a specific shop.
 * Automatically creates a default config if none exists.
 * @param {string} shopId - Shop identifier
 * @param {string} token - Bearer token for authentication
 * @returns {Promise} Bot configuration object
 */
export const getBotConfig = async (shopId, token) => {
  const response = await botConfigApi.get(`/bot-configurations/${shopId}/`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Create or fully replace bot configuration.
 * @param {Object} data - Configuration data (must include shop_id)
 * @param {string} data.shop_id - Shop identifier
 * @param {string} [data.shop_name] - Display name for shop
 * @param {string} [data.language] - Language mode (AUTO/FR/AR/EN)
 * @param {string} [data.ai_agent_name] - Bot display name
 * @param {string} token - Bearer token
 * @returns {Promise} Updated configuration
 */
export const updateBotConfig = async (data, token) => {
  const response = await botConfigApi.put('/bot-configurations/', data, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Partially update bot configuration.
 * Only updates provided fields, leaves others unchanged.
 * @param {Object} data - Partial configuration data (must include shop_id)
 * @param {string} data.shop_id - Shop identifier
 * @param {string} token - Bearer token
 * @returns {Promise} Updated configuration
 */
export const patchBotConfig = async (data, token) => {
  const response = await botConfigApi.patch('/bot-configurations/', data, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};
