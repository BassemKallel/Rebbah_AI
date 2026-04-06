import api from './axiosInstance';

/**
 * Get bot configuration for a specific shop.
 * Automatically creates a default config if none exists.
 */
export const getBotConfig = async (shopId: string) => {
  const response = await api.get(`/api/v1/crm/bot-configurations/${shopId}/`);
  return response.data;
};

/**
 * Create or fully replace bot configuration.
 */
export const updateBotConfig = async (data: Record<string, unknown>) => {
  const response = await api.put('/api/v1/crm/bot-configurations/', data);
  return response.data;
};

/**
 * Partially update bot configuration.
 */
export const patchBotConfig = async (data: Record<string, unknown>) => {
  const response = await api.patch('/api/v1/crm/bot-configurations/', data);
  return response.data;
};
