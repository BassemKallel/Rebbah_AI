/**
 * botConfigService.ts — Bot Configuration API client using the shared JWT axiosInstance.
 */
import api from './axiosInstance';

const CRM = '/api/v1/crm';

/**
 * Get bot configuration for a specific shop.
 * Automatically creates a default config if none exists.
 */
export const getBotConfig = async (shopId: string) => {
  const response = await api.get(`${CRM}/bot-configurations/${shopId}/`);
  return response.data;
};

/**
 * Create or fully replace bot configuration.
 * @param data - Configuration data (must include shop_id)
 */
export const updateBotConfig = async (data: Record<string, unknown>) => {
  const response = await api.put(`${CRM}/bot-configurations/`, data);
  return response.data;
};

/**
 * Partially update bot configuration.
 * Only updates provided fields, leaves others unchanged.
 * @param data - Partial configuration data (must include shop_id)
 */
export const patchBotConfig = async (data: Record<string, unknown>) => {
  const response = await api.patch(`${CRM}/bot-configurations/`, data);
  return response.data;
};
