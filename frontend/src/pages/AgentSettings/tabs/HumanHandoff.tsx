import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, Power, PowerOff, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../../../api/axiosInstance';
import { toggleBot } from '../../../api/handoffApi';

interface BotConfig {
  bot_enabled: boolean;
  bot_disabled_at: string | null;
  shop_name: string;
}

const HumanHandoff = () => {
  const shopId = process.env.REACT_APP_SHOP_ID || '';
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  /* ── Load current bot config ── */
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/api/v1/crm/bot-configurations/${shopId}/`);
      setConfig(data);
    } catch (err) {
      setToast({ type: 'error', message: 'Impossible de charger la configuration du bot.' });
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  /* ── Toggle bot ── */
  const handleToggle = async (enable: boolean) => {
    if (!config) return;
    setSaving(true);
    setToast(null);
    try {
      const { data } = await toggleBot(shopId, enable);
      setConfig(prev => prev ? { ...prev, bot_enabled: data.bot_enabled, bot_disabled_at: data.bot_disabled_at } : prev);
      setToast({
        type: 'success',
        message: enable
          ? 'Bot reactivé — il répond à nouveau automatiquement.'
          : 'Bot désactivé — toutes les conversations sont en mode manuel.',
      });
    } catch (err) {
      setToast({ type: 'error', message: 'Impossible de modifier l\'état du bot.' });
    } finally {
      setSaving(false);
    }
  };

  /* ── Auto-dismiss toast ── */
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  if (loading) {
    return (
      <div className="max-w-3xl flex items-center justify-center py-20">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-[#0f6885] animate-spin" />
          <p className="text-gray-500 font-medium">Chargement...</p>
        </div>
      </div>
    );
  }

  const botEnabled = config?.bot_enabled ?? true;

  return (
    <div className="max-w-3xl">

      {/* Toast */}
      {toast && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl mb-6 text-sm font-medium border ${
          toast.type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : 'bg-red-50 border-red-200 text-red-800'
        }`}>
          {toast.type === 'success'
            ? <CheckCircle className="w-4 h-4 flex-shrink-0" />
            : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
          {toast.message}
        </div>
      )}

      <h1 className="text-[22px] font-extrabold text-gray-800 mb-1">Human Handoff</h1>
      <p className="text-[15px] font-medium text-gray-400 mb-8">
        Contrôlez si le bot répond automatiquement ou si vous gérez les conversations manuellement.
      </p>

      {/* Global Bot Toggle Card */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-6 mb-5 bg-white">
        <div className="flex items-center gap-3 mb-6">
          <div className={`w-5 h-5 rounded-md flex-shrink-0 ${botEnabled ? 'bg-emerald-500' : 'bg-red-400'}`} />
          <h3 className="text-base font-bold text-gray-800">Statut du Bot Global</h3>
        </div>

        {/* Status indicator */}
        <div className={`flex items-center justify-between p-5 rounded-xl border-2 transition-all ${
          botEnabled
            ? 'bg-emerald-50 border-emerald-200'
            : 'bg-amber-50 border-amber-200'
        }`}>
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
              botEnabled ? 'bg-emerald-100' : 'bg-amber-100'
            }`}>
              {botEnabled
                ? <Power className="w-6 h-6 text-emerald-600" />
                : <PowerOff className="w-6 h-6 text-amber-600" />
              }
            </div>
            <div>
              <p className={`text-base font-bold ${botEnabled ? 'text-emerald-800' : 'text-amber-800'}`}>
                {botEnabled ? 'Bot actif' : 'Bot désactivé'}
              </p>
              <p className={`text-sm mt-0.5 ${botEnabled ? 'text-emerald-600' : 'text-amber-600'}`}>
                {botEnabled
                  ? 'Le bot répond automatiquement à tous les messages entrants.'
                  : `Bot arrêté${config?.bot_disabled_at ? ' depuis ' + new Date(config.bot_disabled_at).toLocaleString('fr-FR') : ''} — réponses manuelles uniquement.`
                }
              </p>
            </div>
          </div>

          {/* Toggle switch */}
          <button
            onClick={() => handleToggle(!botEnabled)}
            disabled={saving}
            aria-label={botEnabled ? 'Désactiver le bot' : 'Réactiver le bot'}
            className={`relative w-14 h-7 rounded-full transition-all duration-200 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed ${
              botEnabled
                ? 'bg-emerald-500 focus:ring-emerald-400'
                : 'bg-gray-300 focus:ring-gray-400'
            }`}
          >
            <span className={`absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform duration-200 flex items-center justify-center ${
              botEnabled ? 'translate-x-7' : 'translate-x-0'
            }`}>
              {saving && <Loader2 className="w-3.5 h-3.5 text-gray-400 animate-spin" />}
            </span>
          </button>
        </div>

        <p className="text-xs text-gray-400 mt-4 leading-relaxed">
          Désactiver le bot globalement met <strong>toutes</strong> les conversations en mode manuel.
          Les messages des clients seront enregistrés mais aucune réponse automatique ne sera envoyée.
          Utilisez le bouton «&nbsp;Prendre le relais&nbsp;» dans l'inbox pour contrôler chaque conversation individuellement.
        </p>
      </div>

      {/* Per-conversation explanation */}
      <div className="border border-gray-100 shadow-sm rounded-2xl p-6 bg-white">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-5 h-5 rounded-md bg-[#0f6885] flex-shrink-0" />
          <h3 className="text-base font-bold text-gray-800">Handoff par conversation</h3>
        </div>
        <p className="text-sm text-gray-500 leading-relaxed">
          Pour prendre le relais sur <strong>une conversation précise</strong>, ouvrez-la dans l'
          <a href="/messenger" className="text-[#0f6885] font-semibold hover:underline">Inbox Messenger</a>
          {' '}et cliquez sur le bouton <strong>«&nbsp;Prendre le relais&nbsp;»</strong> dans l'en-tête de la conversation.
          Vous pourrez alors envoyer des messages directement via Messenger.
        </p>
        <div className="mt-4 flex flex-col gap-2 text-sm">
          <div className="flex items-center gap-2 text-gray-600">
            <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
            Bouton vert — Bot actif sur cette conversation
          </div>
          <div className="flex items-center gap-2 text-gray-600">
            <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
            Badge orange — Conversation gérée manuellement
          </div>
        </div>
      </div>
    </div>
  );
};

export default HumanHandoff;
