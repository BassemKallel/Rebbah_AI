import api from './axiosInstance';

/** Get list of templates with optional filtering. */
export const getTemplates = async (filters: Record<string, any> = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, String(value));
    }
  });
  const response = await api.get('/api/v1/crm/templates/', { params });
  return response.data;
};

/** Get a specific template by ID. */
export const getTemplate = async (id: number) => {
  const response = await api.get(`/api/v1/crm/templates/${id}/`);
  return response.data;
};

/** Create a new template (shop-specific override). */
export const createTemplate = async (data: Record<string, unknown>) => {
  const response = await api.post('/api/v1/crm/templates/', data);
  return response.data;
};

/** Update an existing template. */
export const updateTemplate = async (id: number, data: Record<string, unknown>) => {
  const response = await api.put(`/api/v1/crm/templates/${id}/`, data);
  return response.data;
};

/** Delete a shop-specific template. */
export const deleteTemplate = async (id: number) => {
  await api.delete(`/api/v1/crm/templates/${id}/`);
};

/** Preview a template with variables replaced. */
export const previewTemplate = async (id: number, variables: Record<string, string>) => {
  const response = await api.post(`/api/v1/crm/templates/${id}/preview/`, { variables });
  return response.data;
};
