import React, { useState } from 'react';
import {
  User, Building2, Key,
  CheckCircle, Copy, Check, Eye, EyeOff, Loader2
} from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';
import api from '../../api/axiosInstance';
import toast from 'react-hot-toast';

const Profile: React.FC = () => {
  const { username, companyName, shopId } = useAuth();
  const [copied, setCopied] = useState(false);

  // ── Change password form state ──────────────────────────────────────
  const [pwForm, setPwForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pwLoading, setPwLoading] = useState(false);

  const initials = username ? username.slice(0, 2).toUpperCase() : 'TK';

  const handleCopyShopId = () => {
    if (shopId) {
      navigator.clipboard.writeText(shopId);
      setCopied(true);
      toast.success('Shop ID copié !', { icon: '📋' });
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handlePwChange = (field: string, value: string) => {
    setPwForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!pwForm.current_password || !pwForm.new_password || !pwForm.confirm_password) {
      toast.error('Tous les champs sont requis.');
      return;
    }
    if (pwForm.new_password !== pwForm.confirm_password) {
      toast.error('Les nouveaux mots de passe ne correspondent pas.');
      return;
    }
    if (pwForm.new_password.length < 8) {
      toast.error('Le nouveau mot de passe doit contenir au moins 8 caractères.');
      return;
    }

    setPwLoading(true);
    try {
      await api.post('/api/v1/auth/change-password/', {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
        confirm_password: pwForm.confirm_password,
      });
      toast.success('Mot de passe modifié avec succès !');
      setPwForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Une erreur est survenue.');
    } finally {
      setPwLoading(false);
    }
  };

  // Strength indicator
  const strength = (() => {
    const p = pwForm.new_password;
    if (!p) return null;
    if (p.length < 8) return { label: 'Trop court', color: 'bg-red-400', width: '25%' };
    const has = [/[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((r) => r.test(p)).length;
    if (has === 0) return { label: 'Faible', color: 'bg-orange-400', width: '40%' };
    if (has === 1) return { label: 'Moyen', color: 'bg-yellow-400', width: '65%' };
    return { label: 'Fort', color: 'bg-emerald-500', width: '100%' };
  })();

  return (
    <div className="min-h-full bg-gray-50 px-4 sm:px-6 lg:px-8 py-5 sm:py-6 pb-8">

      {/* Page header */}
      <div className="mb-7">
        <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900">Mon profil</h1>
        <p className="text-sm text-gray-400 mt-0.5">Informations de votre compte et de votre boutique</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 sm:gap-6">

        {/* ── Left — Identity card ── */}
        <div className="xl:col-span-1 flex flex-col gap-5">

          {/* Avatar card */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            <div className="h-20 bg-gradient-to-r from-[#0f6885] to-[#0d8fa9]" />
            <div className="px-6 pb-5">
              <div className="-mt-8 mb-4">
                <div className="w-16 h-16 rounded-2xl bg-white shadow-md flex items-center justify-center ring-4 ring-white">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#0f6885] to-[#0d8fa9] flex items-center justify-center">
                    <span className="text-xl font-extrabold text-white">{initials}</span>
                  </div>
                </div>
              </div>
              <h2 className="text-lg font-extrabold text-gray-900">{username || '—'}</h2>
              <p className="text-sm text-gray-400 mt-0.5">{companyName || 'TikTak AI'}</p>
              <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-100 rounded-lg">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                <span className="text-xs font-semibold text-emerald-700">Compte actif</span>
              </div>
            </div>
          </div>

          {/* Account info */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
            <h3 className="text-sm font-bold text-gray-700 mb-4">Informations du compte</h3>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-blue-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] text-gray-400 font-medium">Nom d'utilisateur</p>
                  <p className="text-[13px] font-bold text-gray-800 truncate">{username || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#eef6f9] flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-4 h-4 text-[#0f6885]" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] text-gray-400 font-medium">Boutique</p>
                  <p className="text-[13px] font-bold text-gray-800 truncate">{companyName || '—'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right — Details ── */}
        <div className="xl:col-span-2 flex flex-col gap-5">

          {/* Company / shop info */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5 sm:p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-[#eef6f9] flex items-center justify-center flex-shrink-0">
                <Building2 className="w-4 h-4 text-[#0f6885]" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-800">Boutique</h3>
                <p className="text-xs text-gray-400">Informations de votre boutique TikTak PRO</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Nom de la boutique</p>
                <p className="text-[14px] font-bold text-gray-800">{companyName || '—'}</p>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Shop ID</p>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[13px] font-bold text-gray-800 font-mono truncate">{shopId || '—'}</p>
                  <button
                    onClick={handleCopyShopId}
                    title="Copier le Shop ID"
                    className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors flex-shrink-0"
                  >
                    {copied
                      ? <Check className="w-3.5 h-3.5 text-emerald-500" />
                      : <Copy className="w-3.5 h-3.5 text-gray-400" />
                    }
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── Change Password ── */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5 sm:p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center flex-shrink-0">
                <Key className="w-4 h-4 text-purple-500" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-800">Changer le mot de passe</h3>
                <p className="text-xs text-gray-400">Modifiez votre mot de passe de connexion</p>
              </div>
            </div>

            <form onSubmit={handleChangePassword} className="flex flex-col gap-4">

              {/* Current password */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5">Mot de passe actuel</label>
                <div className="relative">
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    value={pwForm.current_password}
                    onChange={(e) => handlePwChange('current_password', e.target.value)}
                    placeholder="Votre mot de passe actuel"
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 pr-10 text-sm text-gray-700 placeholder-gray-300 focus:outline-none focus:border-[#0f6885] focus:bg-white transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrent((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5">Nouveau mot de passe</label>
                <div className="relative">
                  <input
                    type={showNew ? 'text' : 'password'}
                    value={pwForm.new_password}
                    onChange={(e) => handlePwChange('new_password', e.target.value)}
                    placeholder="Minimum 8 caractères"
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 pr-10 text-sm text-gray-700 placeholder-gray-300 focus:outline-none focus:border-[#0f6885] focus:bg-white transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {/* Strength bar */}
                {strength && (
                  <div className="mt-2">
                    <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${strength.color}`}
                        style={{ width: strength.width }}
                      />
                    </div>
                    <p className={`text-[11px] font-semibold mt-1 ${
                      strength.label === 'Fort' ? 'text-emerald-600' :
                      strength.label === 'Moyen' ? 'text-yellow-600' : 'text-red-500'
                    }`}>
                      {strength.label}
                    </p>
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1.5">Confirmer le nouveau mot de passe</label>
                <div className="relative">
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={pwForm.confirm_password}
                    onChange={(e) => handlePwChange('confirm_password', e.target.value)}
                    placeholder="Répétez le nouveau mot de passe"
                    className={`w-full bg-gray-50 border rounded-xl px-4 py-2.5 pr-10 text-sm text-gray-700 placeholder-gray-300 focus:outline-none transition-colors
                      ${pwForm.confirm_password && pwForm.new_password !== pwForm.confirm_password
                        ? 'border-red-300 focus:border-red-400'
                        : 'border-gray-200 focus:border-[#0f6885] focus:bg-white'
                      }`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {pwForm.confirm_password && pwForm.new_password !== pwForm.confirm_password && (
                  <p className="text-[11px] text-red-500 font-semibold mt-1">Les mots de passe ne correspondent pas</p>
                )}
              </div>

              {/* Submit */}
              <div className="flex justify-end pt-1">
                <button
                  type="submit"
                  disabled={pwLoading}
                  className="flex items-center gap-2 bg-[#0f6885] hover:bg-[#0d5a74] disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-sm font-bold py-2.5 px-6 rounded-xl transition-all active:scale-95 shadow-sm"
                >
                  {pwLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {pwLoading ? 'Modification…' : 'Changer le mot de passe'}
                </button>
              </div>
            </form>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Profile;
