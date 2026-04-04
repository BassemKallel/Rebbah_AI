import React, { useState } from 'react';
import {
  X, Edit3, Save, Loader, Trash2,
  User, Phone, MapPin, Package, Hash, ShoppingBag, Clock, MessageCircle,
} from 'lucide-react';
import type { Lead } from '../../types';
import { STATUS_OPTIONS } from '../../constants/leads';
import { getPlatformInfo, getStatusValue, getStatusConfig } from '../../utils/leads';
import { patchLead as updateLeadApi } from '../../api/crmApi';
import FieldRow from './FieldRow';

interface LeadPanelProps {
  lead: Lead;
  onClose: () => void;
  onSaved: (updated: Lead) => void;
  onDelete: (lead: Lead) => void;
}

const LeadPanel: React.FC<LeadPanelProps> = ({ lead, onClose, onSaved, onDelete }) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    name: lead.name || '',
    phone_number: lead.phone_number || '',
    address: lead.address || '',
    color: lead.color || '',
    size: lead.size || '',
    quantity: lead.quantity || '',
    _status: getStatusValue(lead),
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const statusOpt = STATUS_OPTIONS.find((o) => o.value === form._status);
      const payload = {
        name: form.name,
        phone_number: form.phone_number,
        address: form.address,
        color: form.color,
        size: form.size,
        quantity: form.quantity,
        ...(statusOpt ? {
          has_pending_order: statusOpt.has_pending_order,
          agent_confirmation_pending: statusOpt.agent_confirmation_pending,
        } : {}),
      };
      const { data } = await updateLeadApi(lead.id, payload);
      onSaved(data);
      setEditing(false);
    } catch {
      setError('Erreur lors de la sauvegarde.');
    } finally {
      setSaving(false);
    }
  };

  const cancel = () => {
    setForm({
      name: lead.name || '',
      phone_number: lead.phone_number || '',
      address: lead.address || '',
      color: lead.color || '',
      size: lead.size || '',
      quantity: lead.quantity || '',
      _status: getStatusValue(lead),
    });
    setEditing(false);
    setError(null);
  };

  const platform = getPlatformInfo(lead.platform_id);
  const status = getStatusConfig(lead);
  const initials = (lead.name || '?')[0].toUpperCase();

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200 overflow-hidden">

      {/* Panel header */}
      <div className="flex-shrink-0 px-5 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-widest">Détails du lead</span>
          <button onClick={onClose}
            className="p-1.5 hover:bg-gray-100 rounded-xl transition-colors text-gray-400 hover:text-gray-700">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Avatar + name */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#0f6885] to-[#1a8aac] flex items-center justify-center flex-shrink-0 shadow-lg">
            <span className="text-xl font-bold text-white">{initials}</span>
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-bold text-gray-900 truncate">{lead.name || '—'}</h2>
            <p className="text-xs text-gray-400 mt-0.5 truncate">{lead.platform_id}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${platform.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${platform.dot}`} />
                {platform.label}
              </span>
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border ${status.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
                {status.label}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

        {/* Status section */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Statut</h3>
          <div className="bg-gray-50 rounded-2xl px-4 py-3">
            {editing ? (
              <select name="_status" value={form._status} onChange={handle}
                className="w-full text-sm text-gray-800 bg-white border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-[#0f6885] transition-colors cursor-pointer">
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            ) : (
              <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${status.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${status.dot}`} />
                {status.label}
              </div>
            )}
          </div>
        </div>

        {/* Contact section */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Contact</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            <FieldRow icon={User} label="Nom" name="name" value={form.name} editing={editing} onChange={handle} />
            <FieldRow icon={Phone} label="Téléphone" name="phone_number" value={form.phone_number} editing={editing} onChange={handle} />
            <FieldRow icon={MapPin} label="Adresse" name="address" value={form.address} editing={editing} onChange={handle} />
          </div>
        </div>

        {/* Product section */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Produit</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            {lead.product_id && (
              <FieldRow icon={Package} label="ID Produit" name="product_id" value={lead.product_id} editing={false} onChange={() => {}} />
            )}
            {lead.variation_id && (
              <FieldRow icon={Hash} label="Variation" name="variation_id" value={lead.variation_id} editing={false} onChange={() => {}} />
            )}
            <FieldRow icon={Package} label="Couleur" name="color" value={form.color} editing={editing} onChange={handle} />
            <FieldRow icon={Hash} label="Taille" name="size" value={form.size} editing={editing} onChange={handle} />
            <FieldRow icon={ShoppingBag} label="Quantité" name="quantity" value={String(form.quantity)} type="number" editing={editing} onChange={handle} />
          </div>
        </div>

        {/* Order section */}
        {lead.pending_order_reference && (
          <div>
            <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Commande</h3>
            <div className="bg-gray-50 rounded-2xl px-4">
              <FieldRow icon={ShoppingBag} label="Référence" name="ref" value={lead.pending_order_reference} editing={false} onChange={() => {}} />
              {lead.pending_order_created_at && (
                <FieldRow icon={Clock} label="Date" name="date"
                  value={new Date(lead.pending_order_created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' })}
                  editing={false} onChange={() => {}} />
              )}
            </div>
          </div>
        )}

        {/* IDs */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Identifiants</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            <FieldRow icon={Hash} label="ID Lead" name="id" value={`#${lead.id}`} editing={false} onChange={() => {}} />
            <FieldRow icon={MessageCircle} label="Platform ID" name="platform_id" value={lead.platform_id} editing={false} onChange={() => {}} />
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>
        )}
      </div>

      {/* Footer actions */}
      <div className="flex-shrink-0 px-5 py-4 border-t border-gray-100 bg-white space-y-2">
        {editing ? (
          <div className="flex gap-2">
            <button onClick={cancel} disabled={saving}
              className="flex-1 px-4 py-2.5 text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors disabled:opacity-50">
              Annuler
            </button>
            <button onClick={save} disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors disabled:opacity-50 shadow-sm">
              {saving ? <Loader className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Enregistrement…' : 'Enregistrer'}
            </button>
          </div>
        ) : (
          <button onClick={() => setEditing(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors shadow-sm">
            <Edit3 className="w-4 h-4" />
            Modifier ce lead
          </button>
        )}
        <button onClick={() => onDelete(lead)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-colors">
          <Trash2 className="w-4 h-4" />
          Supprimer ce lead
        </button>
      </div>
    </div>
  );
};

export default LeadPanel;
