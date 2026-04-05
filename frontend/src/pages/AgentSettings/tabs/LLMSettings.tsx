import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../providers/AuthProvider';
import { getCompanySettings, updateCompanySettings, CompanySettings } from '../../../api/companyApi';
import { Zap, Brain, Key, FileText, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';

export default function LLMSettings() {
  const { shopId } = useAuth();
  const [settings, setSettings] = useState<CompanySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [responseMode, setResponseMode] = useState<'nlu' | 'llm'>('nlu');
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [llmContext, setLlmContext] = useState('');

  useEffect(() => {
    if (!shopId) return;
    (async () => {
      try {
        const data = await getCompanySettings(shopId);
        setSettings(data);
        setResponseMode(data.response_mode);
        setLlmContext(data.llm_context || '');
      } catch {
        setError('Impossible de charger la configuration.');
      } finally {
        setLoading(false);
      }
    })();
  }, [shopId]);

  const handleSave = async () => {
    if (!shopId) return;
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      const patch: Record<string, string> = {
        response_mode: responseMode,
        llm_context: llmContext,
      };
      if (geminiApiKey.trim()) {
        patch.gemini_api_key = geminiApiKey;
      }
      const updated = await updateCompanySettings(shopId, patch);
      setSettings(updated);
      setGeminiApiKey('');
      setSuccess('Configuration sauvegardée avec succès !');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      const msg = err?.response?.data?.non_field_errors?.[0]
        || err?.response?.data?.error
        || JSON.stringify(err?.response?.data)
        || 'Erreur lors de la sauvegarde.';
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#6366f1' }} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1f2937', marginBottom: 4 }}>
        Mode de réponse IA
      </h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: 28 }}>
        Choisissez comment le bot répond aux clients de votre boutique.
      </p>

      {/* ── Mode Selector ── */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 28, flexWrap: 'wrap' }}>
        {/* NLU Card */}
        <button
          onClick={() => setResponseMode('nlu')}
          style={{
            flex: 1, minWidth: 260, padding: '20px 20px', borderRadius: 14, cursor: 'pointer',
            border: responseMode === 'nlu' ? '2px solid #0f6885' : '2px solid #e5e7eb',
            background: responseMode === 'nlu' ? '#eef6f9' : '#fff',
            textAlign: 'left', transition: 'all 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Zap style={{ color: responseMode === 'nlu' ? '#0f6885' : '#9ca3af', width: 20, height: 20 }} />
            <span style={{ fontWeight: 700, fontSize: 15, color: responseMode === 'nlu' ? '#0f6885' : '#374151' }}>
              Pipeline NLU
            </span>
            {responseMode === 'nlu' && <CheckCircle style={{ color: '#0f6885', width: 16, height: 16, marginLeft: 'auto' }} />}
          </div>
          <p style={{ color: '#6b7280', fontSize: 13, margin: 0, lineHeight: 1.5 }}>
            TunBERT + GLiNER — Analyse fine du dialecte tunisien, machine à états pour les commandes, product lookup réel.
          </p>
        </button>

        {/* LLM Card */}
        <button
          onClick={() => setResponseMode('llm')}
          style={{
            flex: 1, minWidth: 260, padding: '20px 20px', borderRadius: 14, cursor: 'pointer',
            border: responseMode === 'llm' ? '2px solid #7c3aed' : '2px solid #e5e7eb',
            background: responseMode === 'llm' ? '#f5f3ff' : '#fff',
            textAlign: 'left', transition: 'all 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <Brain style={{ color: responseMode === 'llm' ? '#7c3aed' : '#9ca3af', width: 20, height: 20 }} />
            <span style={{ fontWeight: 700, fontSize: 15, color: responseMode === 'llm' ? '#7c3aed' : '#374151' }}>
              LLM Direct (Gemini)
            </span>
            {responseMode === 'llm' && <CheckCircle style={{ color: '#7c3aed', width: 16, height: 16, marginLeft: 'auto' }} />}
          </div>
          <p style={{ color: '#6b7280', fontSize: 13, margin: 0, lineHeight: 1.5 }}>
            Réponses générées par IA avec votre contexte. Peut aussi créer des commandes automatiquement.
          </p>
        </button>
      </div>

      {/* ── Gemini API Key ── */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 14, color: '#374151', marginBottom: 8 }}>
          <Key style={{ width: 16, height: 16, color: '#6366f1' }} />
          Clé API Gemini
          {settings?.has_gemini_key && (
            <span style={{
              fontSize: 11, background: '#d1fae5', color: '#065f46',
              padding: '2px 8px', borderRadius: 6, fontWeight: 600,
            }}>
              ✓ Configurée
            </span>
          )}
        </label>
        <input
          type="password"
          placeholder={settings?.has_gemini_key ? '••••••••••••••••••••••' : 'AIzaSy...'}
          value={geminiApiKey}
          onChange={(e) => setGeminiApiKey(e.target.value)}
          style={{
            width: '100%', padding: '10px 14px', borderRadius: 10,
            border: '1px solid #e5e7eb', fontSize: 14, fontFamily: 'monospace',
            outline: 'none', boxSizing: 'border-box',
          }}
        />
        <p style={{ color: '#9ca3af', fontSize: 12, marginTop: 4 }}>
          Votre clé est chiffrée en base de données (AES-256). Elle n'est jamais exposée via l'API.
        </p>
      </div>

      {/* ── LLM Context ── */}
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 14, color: '#374151', marginBottom: 8 }}>
          <FileText style={{ width: 16, height: 16, color: '#6366f1' }} />
          Contexte de la boutique
          <span style={{
            fontSize: 12, color: llmContext.length > 10000 ? '#ef4444' : '#9ca3af',
            marginLeft: 'auto', fontWeight: 500, fontFamily: 'monospace',
          }}>
            {llmContext.length.toLocaleString()} / 10 000
          </span>
        </label>
        <textarea
          value={llmContext}
          onChange={(e) => setLlmContext(e.target.value)}
          maxLength={10000}
          rows={10}
          placeholder={`Ex:\nNom de la boutique : Iconic Store\nProduits : T-shirts, Pulls, Vestes\nLivraison : 7 TND, 2-3 jours ouvrables\nRetours : Échange sous 7 jours\nHoraires : Lun-Sam 9h-18h\nFAQ : ...\n\nLe bot utilisera ce texte pour répondre aux clients.`}
          style={{
            width: '100%', padding: '12px 14px', borderRadius: 10,
            border: '1px solid #e5e7eb', fontSize: 14, fontFamily: "'Inter', sans-serif",
            lineHeight: 1.6, resize: 'vertical', outline: 'none',
            boxSizing: 'border-box', minHeight: 200,
          }}
        />
      </div>

      {/* ── Warning ── */}
      {responseMode === 'llm' && (
        <div style={{
          display: 'flex', gap: 12, padding: '14px 16px', borderRadius: 12,
          background: '#fef3c7', border: '1px solid #fde68a', marginBottom: 24,
        }}>
          <AlertTriangle style={{ width: 18, height: 18, color: '#d97706', flexShrink: 0, marginTop: 2 }} />
          <div style={{ fontSize: 13, color: '#92400e', lineHeight: 1.6 }}>
            <strong>En mode LLM Direct :</strong> Le bot utilise votre clé API Gemini.
            Les coûts de consommation sont à votre charge. Assurez-vous que le contexte
            est complet pour des réponses de qualité.
          </div>
        </div>
      )}

      {/* ── Messages ── */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, marginBottom: 16,
          background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13,
        }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, marginBottom: 16,
          background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#16a34a', fontSize: 13,
        }}>
          {success}
        </div>
      )}

      {/* ── Save Button ── */}
      <button
        onClick={handleSave}
        disabled={saving}
        style={{
          padding: '12px 32px', borderRadius: 10, border: 'none', cursor: 'pointer',
          background: 'linear-gradient(135deg, #0f6885, #0d8fa9)', color: '#fff',
          fontSize: 15, fontWeight: 600, fontFamily: "'Inter', sans-serif",
          opacity: saving ? 0.7 : 1, transition: 'all 0.2s',
          display: 'flex', alignItems: 'center', gap: 8,
        }}
      >
        {saving && <Loader2 className="w-4 h-4 animate-spin" />}
        {saving ? 'Sauvegarde...' : 'Sauvegarder'}
      </button>
    </div>
  );
}
