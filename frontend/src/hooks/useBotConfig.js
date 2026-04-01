import { useState, useEffect } from 'react';
import { getBotConfig, updateBotConfig, patchBotConfig } from '../api/botConfigService';

/**
 * Custom hook for managing bot configuration.
 * Automatically fetches configuration on mount and provides mutation methods.
 * 
 * @param {string} shopId - Shop identifier
 * @param {string} token - Bearer token for authentication
 * @returns {Object} Hook state and methods
 */
export const useBotConfig = (shopId, token) => {
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchConfig = async () => {
        if (!shopId || !token) {
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const data = await getBotConfig(shopId, token);
            setConfig(data);
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Failed to load configuration');
            console.error('Error fetching bot config:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfig();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [shopId, token]);

    /**
     * Fully replace bot configuration.
     * @param {Object} newData - New configuration data
     * @returns {Promise<Object>} Result object with success flag
     */
    const updateConfig = async (newData) => {
        try {
            setLoading(true);
            setError(null);
            const updated = await updateBotConfig({ ...newData, shop_id: shopId }, token);
            setConfig(updated);
            return { success: true, data: updated };
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to update configuration';
            setError(errorMsg);
            console.error('Error updating bot config:', err);
            return { success: false, error: errorMsg };
        } finally {
            setLoading(false);
        }
    };

    /**
     * Partially update bot configuration (only provided fields).
     * @param {Object} partialData - Partial configuration data
     * @returns {Promise<Object>} Result object with success flag
     */
    const patchConfig = async (partialData) => {
        try {
            setLoading(true);
            setError(null);
            const updated = await patchBotConfig({ ...partialData, shop_id: shopId }, token);
            setConfig(updated);
            return { success: true, data: updated };
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to update configuration';
            setError(errorMsg);
            console.error('Error patching bot config:', err);
            return { success: false, error: errorMsg };
        } finally {
            setLoading(false);
        }
    };

    return {
        config,
        loading,
        error,
        updateConfig,
        patchConfig,
        refetch: fetchConfig
    };
};
