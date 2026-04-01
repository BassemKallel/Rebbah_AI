import React, { useState, useEffect } from 'react';
import { Loader2, Save } from 'lucide-react';
import { useBotConfig } from '../../../hooks/useBotConfig';
import Toast from '../../../components/ui/Toast';

const BotConfiguration = () => {
  const shopId = process.env.REACT_APP_SHOP_ID || '1LXybpj';
  const token = process.env.REACT_APP_SHOP_TOKEN;

  const { config, loading, error, patchConfig } = useBotConfig(shopId, token);

  const [formData, setFormData] = useState({
    shop_name: '',
    ai_agent_name: '',
    language: 'AUTO'
  });

  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (config) {
      setFormData({
        shop_name: config.shop_name || '',
        ai_agent_name: config.ai_agent_name || '',
        language: config.language || 'AUTO'
      });
    }
  }, [config]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setToast(null);

    const result = await patchConfig(formData);

    setIsSaving(false);

    if (result.success) {
      setToast({
        type: 'success',
        message: 'Bot configuration saved successfully!'
      });
    } else {
      setToast({
        type: 'error',
        message: result.error || 'Failed to save configuration'
      });
    }
  };

  const languageOptions = [
    { value: 'AUTO', label: 'AUTO - Automatic Detection', description: 'The bot detects and responds in the customer\'s language based on their first message.' },
    { value: 'FR', label: 'FR - Always French', description: 'The bot will always respond in French, regardless of the customer\'s language.' },
    { value: 'AR', label: 'AR - Always Arabic', description: 'The bot will always respond in Arabic, regardless of the customer\'s language.' },
    { value: 'EN', label: 'EN - Always English', description: 'The bot will always respond in English, regardless of the customer\'s language.' }
  ];

  const selectedLanguage = languageOptions.find(opt => opt.value === formData.language) || languageOptions[0];

  if (loading) {
    return (
      <div className="max-w-3xl flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#0f6885] animate-spin" />
          <p className="text-gray-500 font-medium">Loading configuration...</p>
        </div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="max-w-3xl">
        <div className="border border-red-200 bg-red-50 rounded-2xl p-6">
          <h3 className="text-red-800 font-bold mb-2">Error Loading Configuration</h3>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Bot Configuration</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">
        Configure your AI agent's global settings and behavior
      </p>

      {/* Shop Information */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-md bg-[#0f6885] flex-shrink-0" />
          <h3 className="text-base font-bold text-gray-800">Shop Information</h3>
        </div>

        <div className="flex flex-col gap-3">
          <label className="text-sm font-semibold text-gray-500">Shop Name</label>
          <div className="bg-[#f0f4f8] rounded-xl px-4 py-3 border border-transparent hover:border-gray-200 transition-all">
            <input
              type="text"
              value={formData.shop_name}
              onChange={(e) => handleChange('shop_name', e.target.value)}
              placeholder="e.g., Iconic Store"
              className="bg-transparent border-none outline-none text-gray-700 font-medium text-sm w-full"
            />
          </div>
          <p className="text-xs text-gray-400 font-medium">
            This name will be used in bot responses with the {'{shop_name}'} variable.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <label className="text-sm font-semibold text-gray-500">AI Agent Name</label>
          <div className="bg-[#f0f4f8] rounded-xl px-4 py-3 border border-transparent hover:border-gray-200 transition-all">
            <input
              type="text"
              value={formData.ai_agent_name}
              onChange={(e) => handleChange('ai_agent_name', e.target.value)}
              placeholder="e.g., Sara"
              className="bg-transparent border-none outline-none text-gray-700 font-medium text-sm w-full"
            />
          </div>
          <p className="text-xs text-gray-400 font-medium">
            The display name of your AI assistant, used in responses with {'{ai_agent_name}'}.
          </p>
        </div>
      </div>

      {/* Language Settings */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-5 mb-5 flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-md bg-[#6366f1] flex-shrink-0" />
          <h3 className="text-base font-bold text-gray-800">Language Settings</h3>
        </div>

        <div className="flex flex-col gap-3">
          <label className="text-sm font-semibold text-gray-500">Response Language</label>
          <div className="relative">
            <select
              value={formData.language}
              onChange={(e) => handleChange('language', e.target.value)}
              className="w-full bg-[#f0f4f8] rounded-xl px-4 py-3 border border-transparent hover:border-gray-200 transition-all outline-none text-gray-700 font-medium text-sm appearance-none cursor-pointer"
            >
              {languageOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
              <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mt-2">
            <p className="text-sm text-blue-800 font-medium">
              💡 {selectedLanguage.description}
            </p>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end mt-6">
        <button
          onClick={handleSave}
          disabled={isSaving || loading}
          className="bg-[#0f6885] hover:bg-[#0d5a74] disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-bold py-3 px-8 rounded-xl flex items-center gap-2 shadow-sm transition-all active:scale-95"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Saving...</span>
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              <span>Save Changes</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default BotConfiguration;
