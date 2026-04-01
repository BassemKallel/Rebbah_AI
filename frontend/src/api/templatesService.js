import axios from 'axios';

const API_BASE = process.env.REACT_APP_CRM_API_URL || 'http://localhost/api/v1/crm';

const templatesApi = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Get list of templates with optional filtering.
 * @param {Object} filters - Query parameters
 * @param {string} [filters.category] - Filter by category (response, missing_entity, etc.)
 * @param {string} [filters.language] - Filter by language (FR, AR, EN)
 * @param {string} [filters.shop_id] - Filter by shop
 * @param {boolean} [filters.is_default] - Filter system templates only
 * @param {string} token - Bearer token
 * @returns {Promise} List of templates
 */
export const getTemplates = async (filters = {}, token) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      params.append(key, value);
    }
  });
  
  const response = await templatesApi.get('/templates/', {
    params,
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Get a specific template by ID.
 * @param {number} id - Template ID
 * @param {string} token - Bearer token
 * @returns {Promise} Template object
 */
export const getTemplate = async (id, token) => {
  const response = await templatesApi.get(`/templates/${id}/`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Create a new template (shop-specific override).
 * @param {Object} data - Template data
 * @param {string} data.category - Category (response, missing_entity, etc.)
 * @param {string} data.sub_key - Sub-key identifier (GREETING, size, etc.)
 * @param {string} data.language - Language (FR, AR, EN)
 * @param {string} data.content - Template content with {variables}
 * @param {string} [data.shop_id] - Shop ID for shop-specific template
 * @param {string} token - Bearer token
 * @returns {Promise} Created template
 */
export const createTemplate = async (data, token) => {
  const response = await templatesApi.post('/templates/', data, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Update an existing template.
 * System templates (is_default=true) cannot be modified.
 * @param {number} id - Template ID
 * @param {Object} data - Updated template data
 * @param {string} token - Bearer token
 * @returns {Promise} Updated template
 */
export const updateTemplate = async (id, data, token) => {
  const response = await templatesApi.put(`/templates/${id}/`, data, {
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

/**
 * Delete a shop-specific template.
 * System templates cannot be deleted.
 * @param {number} id - Template ID
 * @param {string} token - Bearer token
 * @returns {Promise} void
 */
export const deleteTemplate = async (id, token) => {
  await templatesApi.delete(`/templates/${id}/`, {
    headers: { Authorization: `Bearer ${token}` }
  });
};

/**
 * Preview a template with variables replaced.
 * @param {number} id - Template ID
 * @param {Object} variables - Variable values to substitute
 * @param {string} token - Bearer token
 * @returns {Promise} Preview object with 'preview' field
 */
export const previewTemplate = async (id, variables, token) => {
  const response = await templatesApi.post(
    `/templates/${id}/preview/`,
    { variables },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.data;
};
