import { useState, useEffect } from 'react';
import {
    getTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate
} from '../api/templatesService';

/**
 * Custom hook for managing response templates.
 * Automatically fetches templates on mount and provides CRUD methods.
 * 
 * @param {Object} filters - Query filters (category, language, shop_id, is_default)
 * @param {string} token - Bearer token for authentication
 * @returns {Object} Hook state and methods
 */
export const useTemplates = (filters = {}, token) => {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchTemplates = async () => {
        if (!token) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data = await getTemplates(filters, token);
            setTemplates(Array.isArray(data) ? data : (data.results || []));
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Failed to load templates');
            console.error('Error fetching templates:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTemplates();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [JSON.stringify(filters), token]);

    /**
     * Create a new template (shop-specific override).
     * @param {Object} templateData - Template data
     * @returns {Promise<Object>} Result object with success flag
     */
    const create = async (templateData) => {
        try {
            setError(null);
            const newTemplate = await createTemplate(templateData, token);
            setTemplates([...templates, newTemplate]);
            return { success: true, data: newTemplate };
        } catch (err) {
            const errorMsg = err.response?.data?.detail ||
                err.response?.data?.error ||
                err.message ||
                'Failed to create template';
            setError(errorMsg);
            console.error('Error creating template:', err);
            return { success: false, error: errorMsg };
        }
    };

    /**
     * Update an existing template.
     * @param {number} id - Template ID
     * @param {Object} templateData - Updated template data
     * @returns {Promise<Object>} Result object with success flag
     */
    const update = async (id, templateData) => {
        try {
            setError(null);
            const updated = await updateTemplate(id, templateData, token);
            setTemplates(templates.map(t => t.id === id ? updated : t));
            return { success: true, data: updated };
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to update template';
            setError(errorMsg);
            console.error('Error updating template:', err);
            return { success: false, error: errorMsg };
        }
    };

    /**
     * Delete a shop-specific template.
     * @param {number} id - Template ID
     * @returns {Promise<Object>} Result object with success flag
     */
    const remove = async (id) => {
        try {
            setError(null);
            await deleteTemplate(id, token);
            setTemplates(templates.filter(t => t.id !== id));
            return { success: true };
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete template';
            setError(errorMsg);
            console.error('Error deleting template:', err);
            return { success: false, error: errorMsg };
        }
    };

    /**
     * Find a template by category, sub_key, and language.
     */
    const findTemplates = (category, subKey, language) => {
        return templates.filter(t =>
            t.template_type === category &&
            t.intent === subKey &&
            t.language === language
        ).sort((a, b) => {
            if (a.is_default && !b.is_default) return -1;
            if (!a.is_default && b.is_default) return 1;
            return 0;
        });
    };

    /**
     * Get system template for a specific category/sub_key/language.
     */
    const getSystemTemplate = (category, subKey, language) => {
        return templates.find(t =>
            t.template_type === category &&
            t.intent === subKey &&
            t.language === language &&
            t.is_default === true
        ) || null;
    };

    /**
     * Get custom (shop-specific) template for a specific category/sub_key/language.
     */
    const getCustomTemplate = (category, subKey, language) => {
        return templates.find(t =>
            t.template_type === category &&
            t.intent === subKey &&
            t.language === language &&
            t.is_default === false
        ) || null;
    };

    return {
        templates,
        loading,
        error,
        create,
        update,
        remove,
        refetch: fetchTemplates,
        findTemplates,
        getSystemTemplate,
        getCustomTemplate
    };
};
