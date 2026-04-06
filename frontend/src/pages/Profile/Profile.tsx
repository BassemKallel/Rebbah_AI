import React, { useState } from 'react';
import {
  User, Building2, Key, Shield,
  CheckCircle, Copy, Check
} from 'lucide-react';
import { useAuth } from '../../providers/AuthProvider';

const Profile: React.FC = () => {
  const { username, companyName, shopId } = useAuth();
  const [copied, setCopied] = useState(false);

  // Generate initials
  const initials = username ? username.slice(0, 2).toUpperCase() : 'TK';

  const handleCopyShopId = () => {
    if (shopId) {
      navigator.clipboard.writeText(shopId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="min-h-full bg-gray-50 px-4 sm:px-6 lg:px-8 py-5 sm:py-6 pb-8">

      {/* Page header */}
      <div className="mb-7">
        <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900">Mon profil</h1>
        <p className="text-sm text-gray-400 mt-0.5">Informations de votre compte et de votre boutique</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 sm:gap-6">

        {/* Left — Identity card */}
        <div className="xl:col-span-1 flex flex-col gap-5">

          {/* Avatar card */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
            {/* Gradient banner */}
            <div className="h-20 bg-gradient-to-r from-[#0f6885] to-[#0d8fa9]" />
            {/* Avatar */}
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
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center flex-shrink-0">
                  <Shield className="w-4 h-4 text-purple-500" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] text-gray-400 font-medium">Rôle</p>
                  <p className="text-[13px] font-bold text-gray-800">Propriétaire</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right — Details */}
        <div className="xl:col-span-2 flex flex-col gap-5">

          {/* Company info */}
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

          {/* Security */}
          <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5 sm:p-6">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-purple-50 flex items-center justify-center flex-shrink-0">
                <Key className="w-4 h-4 text-purple-500" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-800">Sécurité</h3>
                <p className="text-xs text-gray-400">Authentification et accès à l'API</p>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <div>
                    <p className="text-[13px] font-bold text-gray-800">JWT (Dashboard)</p>
                    <p className="text-[11px] text-gray-400">Session active — expire dans ~50 min</p>
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg border border-emerald-100">Actif</span>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-[#0f6885]" />
                  <div>
                    <p className="text-[13px] font-bold text-gray-800">Dashboard Token (TikTak PRO)</p>
                    <p className="text-[11px] text-gray-400">Token statique pour les webhooks</p>
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-[#0f6885] bg-[#eef6f9] px-2 py-1 rounded-lg border border-[#d6ecf3]">Configuré</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Profile;
