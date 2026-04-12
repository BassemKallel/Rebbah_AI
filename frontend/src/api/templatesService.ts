/**
 * templatesService.ts — Templates API client using the shared JWT axiosInstance.
 *
 * Uses axiosInstance (with JWT interceptor) — no manual token parameter needed.
 */
import api from './axiosInstance';

const CRM = '/api/v1/crm';

/**
 * Get list of templates with optional filtering.
 */
export const getTemplates = async (filters: Record<string, unknown> = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, String(value));
    }
  });
  const response = await api.get(`${CRM}/templates/`, { params });
  return response.data;
};

/**
 * Get a specific template by ID.
 */
export const getTemplate = async (id: number) => {
  const response = await api.get(`${CRM}/templates/${id}/`);
  return response.data;
};

/**
 * Create a new template (shop-specific override).
 */
export const createTemplate = async (data: Record<string, unknown>) => {
  const response = await api.post(`${CRM}/templates/`, data);
  return response.data;
};

/**
 * Update an existing template.
 * System templates (is_default=true) cannot be modified.
 */
export const updateTemplate = async (id: number, data: Record<string, unknown>) => {
  const response = await api.put(`${CRM}/templates/${id}/`, data);
  return response.data;
};

/**
 * Delete a shop-specific template.
 * System templates cannot be deleted.
 */
export const deleteTemplate = async (id: number) => {
  await api.delete(`${CRM}/templates/${id}/`);
};

/**
 * Preview a resolved template via the full lookup chain.
 */
export const previewTemplate = async (
  shopId: string,
  language: string,
  templateType: string,
  intent: string
) => {
  const response = await api.get(`${CRM}/templates/preview/`, {
    params: { shop_id: shopId, language, template_type: templateType, intent },
  });
  return response.data;
};
