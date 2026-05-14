import React, { useState, useEffect } from 'react';
import { Loader2, Save, HelpCircle, Store, Bot, ShieldCheck } from 'lucide-react';
import { useBotConfig } from '../../hooks/useBotConfig';
import Toast from '../../components/ui/Toast';
import { useAuth } from '../../providers/AuthProvider';

const BotConfiguration = () => {
  const { shopId } = useAuth();

  const { config, loading, error, patchConfig } = useBotConfig(shopId);

  const [formData, setFormData] = useState({
    shop_name: '',
    ai_agent_name: '',
    business_domain: '',
    target_audience: '',
    communication_tone: '',
    language_rules: '',
    delivery_policy: '',
    required_checkout_info: '',
    bot_enabled: true
  });

  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<{ type: string; message: string } | null>(null);

  useEffect(() => {
    if (config) {
      setFormData({
        shop_name: config.shop_name || '',
        ai_agent_name: config.ai_agent_name || '',
        business_domain: config.business_domain || '',
        target_audience: config.target_audience || '',
        communication_tone: config.communication_tone || '',
        language_rules: config.language_rules || '',
        delivery_policy: config.delivery_policy || '',
        required_checkout_info: config.required_checkout_info || '',
        bot_enabled: config.bot_enabled !== false
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
    <div className="max-w-4xl mx-auto w-full flex flex-col">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      {/* Shop Information */}
      <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-6 md:p-8 mb-6 flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-[#0f6885]/10 flex items-center justify-center">
             <Store className="w-5 h-5 text-[#0f6885]" />
          </div>
          <div>
             <h3 className="text-lg font-bold text-gray-900">Identité de la Boutique</h3>
             <p className="text-[13px] font-medium text-gray-500">Informations de base utilisées dans le contexte conversationnel</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Nom de la boutique</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Le nom officiel de votre boutique tel qu'il sera communiqué aux clients.
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <input
                type="text"
                value={formData.shop_name}
                onChange={(e) => handleChange('shop_name', e.target.value)}
                placeholder="Ex: Iconic Store"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full placeholder-gray-400"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Nom de l'Agent IA</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-56 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Le prénom que l'IA utilisera pour se présenter de manière humaine.
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <input
                type="text"
                value={formData.ai_agent_name}
                onChange={(e) => handleChange('ai_agent_name', e.target.value)}
                placeholder="Ex: Sara"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full placeholder-gray-400"
              />
            </div>
          </div>
        </div>
      </div>

      {/* LLM Behavior Settings */}
      <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-6 md:p-8 mb-6 flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-[#0f6885]/10 flex items-center justify-center">
             <Bot className="w-5 h-5 text-[#0f6885]" />
          </div>
          <div>
             <h3 className="text-lg font-bold text-gray-900">Personnalité & Ton</h3>
             <p className="text-[13px] font-medium text-gray-500">Définissez comment l'IA interagit avec vos clients</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 mt-2">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Domaine d'activité</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Aide l'IA à comprendre ce qu'elle vend et à adapter son vocabulaire métier (ex: Mode, Électronique).
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={2}
                value={formData.business_domain}
                onChange={(e) => handleChange('business_domain', e.target.value)}
                placeholder="Ex: Magasin de vêtements en ligne"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Public cible</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Définit à qui s'adresse l'IA (ex: Jeunes, Professionnels, Familles) pour ajuster son discours.
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={2}
                value={formData.target_audience}
                onChange={(e) => handleChange('target_audience', e.target.value)}
                placeholder="Ex: Jeunes tunisiens"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Ton de communication</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  L'humeur générale de l'IA (Amical, formel, avec beaucoup d'emojis, etc.).
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={2}
                value={formData.communication_tone}
                onChange={(e) => handleChange('communication_tone', e.target.value)}
                placeholder="Ex: Amical, professionnel"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Règles de langage</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Règles strictes sur la langue à utiliser (Ex: Toujours répondre en Tunisien Arabizi, pas de vouvoiement).
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={3}
                value={formData.language_rules}
                onChange={(e) => handleChange('language_rules', e.target.value)}
                placeholder="Ex: Toujours répondre en Tunisien Arabizi."
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Business Rules */}
      <div className="bg-white border border-gray-200 shadow-sm rounded-xl p-6 md:p-8 mb-6 flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-[#0f6885]/10 flex items-center justify-center">
             <ShieldCheck className="w-5 h-5 text-[#0f6885]" />
          </div>
          <div>
             <h3 className="text-lg font-bold text-gray-900">Politiques & Checkout</h3>
             <p className="text-[13px] font-medium text-gray-500">Règles métier à appliquer lors des ventes</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 mt-2">
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Politique de livraison et de paiement</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-72 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Informations sur les frais de livraison, les délais et les modes de paiement que l'IA donnera si on lui pose la question.
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={4}
                value={formData.delivery_policy}
                onChange={(e) => handleChange('delivery_policy', e.target.value)}
                placeholder="Ex: Livraison partout en Tunisie à 7 TND. Paiement à la livraison."
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-bold text-gray-700">Informations de Checkout requises</label>
              <div className="group relative flex items-center">
                <HelpCircle className="w-3.5 h-3.5 text-gray-400 cursor-help hover:text-[#0f6885] transition-colors" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-72 p-2 bg-gray-800 text-white text-[11px] font-medium rounded-lg shadow-xl z-10 text-center leading-relaxed">
                  Liste des données personnelles (Adresse, Téléphone, Nom) que l'IA doit impérativement obtenir pour valider une commande.
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-lg px-4 py-3 border border-gray-300 focus-within:border-[#0f6885] focus-within:ring-1 focus-within:ring-[#0f6885] transition-all duration-200">
              <textarea
                rows={4}
                value={formData.required_checkout_info}
                onChange={(e) => handleChange('required_checkout_info', e.target.value)}
                placeholder="Ex: 1. Nom 2. Téléphone 3. Adresse"
                className="bg-transparent border-none outline-none text-gray-900 font-medium text-sm w-full resize-y placeholder-gray-400 leading-relaxed"
              />
            </div>
            <p className="text-[12px] text-gray-500 mt-1">
              * L'IA refusera de finaliser une commande tant que ces informations ne seront pas collectées.
            </p>
          </div>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="flex items-center justify-between mt-4 bg-white border border-gray-200 shadow-sm rounded-xl p-6">
        <div className="flex items-center gap-4">
          <label className="relative inline-flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              className="sr-only peer" 
              checked={formData.bot_enabled}
              onChange={(e) => handleChange('bot_enabled', e.target.checked)}
            />
            <div className="w-12 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#0f6885]"></div>
          </label>
          <div>
            <h3 className="text-sm font-bold text-gray-900">{formData.bot_enabled ? 'Agent Actif' : 'Agent Suspendu'}</h3>
            <p className="text-[12px] text-gray-500">{formData.bot_enabled ? 'Réponses automatiques activées' : 'Intervention manuelle requise'}</p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={isSaving || loading}
          className="bg-[#0f6885] hover:bg-[#0c5973] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-bold py-2.5 px-6 rounded-lg flex items-center gap-2 transition-all"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Enregistrement...</span>
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              <span>Enregistrer</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default BotConfiguration;
