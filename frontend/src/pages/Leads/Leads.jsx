import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Search, RefreshCw, Loader, Trash2, Edit3, X, Save,
  ChevronLeft, ChevronRight, User, Package, Phone,
  MapPin, Hash, CheckCircle, Clock, AlertCircle,
  Users, SearchX, WifiOff, Plus, MoreVertical,
  ShoppingBag, MessageCircle
} from 'lucide-react';
import { fetchLeads, patchLead as updateLead, deleteLead } from '../../api/crmApi';

const SHOP_ID = process.env.REACT_APP_SHOP_ID || '';
const PAGE_SIZE = 20;

/* ─── Helpers ────────────────────────────────────────────────────── */
const getPlatformInfo = (platformId = '') => {
  const lower = platformId.toLowerCase();
  if (lower.startsWith('whatsapp'))
    return { label: 'WhatsApp', color: 'bg-green-100 text-green-700', dot: 'bg-green-500' };
  if (lower.startsWith('instagram'))
    return { label: 'Instagram', color: 'bg-pink-100 text-pink-700', dot: 'bg-pink-500' };
  if (lower.startsWith('messenger') || lower.startsWith('facebook'))
    return { label: 'Messenger', color: 'bg-blue-100 text-blue-700', dot: 'bg-blue-500' };
  return { label: platformId.split(':')[0] || '—', color: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400' };
};

const getStatusConfig = (lead) => {
  if (lead.agent_confirmation_pending)
    return { label: 'Confirmation agent', color: 'bg-orange-50 text-orange-700 border-orange-200', dot: 'bg-orange-400' };
  if (lead.has_pending_order)
    return { label: 'En attente', color: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-400' };
  return { label: 'Confirmé', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-400' };
};

const TABS = [
  { key: 'all', label: 'Tous les leads', icon: Users },
  { key: 'pending', label: 'En attente', icon: Clock },
  { key: 'confirmed', label: 'Confirmés', icon: CheckCircle },
  { key: 'agent', label: 'Confirmation agent', icon: AlertCircle },
];
const matchTab = (lead, tab) => {
  if (tab === 'all') return true;
  if (tab === 'pending') return lead.has_pending_order && !lead.agent_confirmation_pending;
  if (tab === 'confirmed') return !lead.has_pending_order && !lead.agent_confirmation_pending;
  if (tab === 'agent') return !!lead.agent_confirmation_pending;
  return true;
};

/* ─── Field Row (for detail panel) ──────────────────────────────── */
const FieldRow = ({ icon: Icon, label, value, name, type = 'text', editing, onChange }) => (
  <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
    <div className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0 mt-0.5">
      <Icon className="w-3.5 h-3.5 text-gray-500" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      {editing ? (
        <input
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          className="w-full text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#0f6885] transition-colors"
        />
      ) : (
        <p className="text-sm font-semibold text-gray-700 truncate">{value || <span className="text-gray-300 font-normal">—</span>}</p>
      )}
    </div>
  </div>
);

/* ─── Delete confirm modal ───────────────────────────────────────── */
const DeleteModal = ({ lead, onClose, onConfirm, deleting }) => {
  useEffect(() => {
    const h = (e) => { if (e.key === 'Escape' && !deleting) onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose, deleting]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4"
      onClick={(e) => { if (e.target === e.currentTarget && !deleting) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        <div className="flex flex-col items-center px-6 pt-8 pb-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
            <Trash2 className="w-7 h-7 text-red-500" />
          </div>
          <h2 className="text-base font-bold text-gray-800 mb-1">Supprimer ce lead&nbsp;?</h2>
          <p className="text-sm text-gray-500 leading-relaxed">
            Vous êtes sur le point de supprimer&nbsp;
            <span className="font-semibold text-gray-700">{lead.name || `#${lead.id}`}</span>.
            Cette action est irréversible.
          </p>
        </div>
        <div className="flex gap-2 px-6 pb-6 pt-2">
          <button onClick={onClose} disabled={deleting}
            className="flex-1 px-4 py-2.5 text-sm font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors disabled:opacity-50">
            Annuler
          </button>
          <button onClick={onConfirm} disabled={deleting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-red-500 hover:bg-red-600 rounded-xl transition-colors disabled:opacity-50">
            {deleting ? <Loader className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            {deleting ? 'Suppression…' : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Right Detail / Edit Panel ─────────────────────────────────── */
const LeadPanel = ({ lead, onClose, onSaved, onDelete }) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    name: lead.name || '',
    phone_number: lead.phone_number || '',
    address: lead.address || '',
    color: lead.color || '',
    size: lead.size || '',
    quantity: lead.quantity || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handle = (e) => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await updateLead(lead.id, form);
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
    });
    setEditing(false);
    setError(null);
  };

  const platform = getPlatformInfo(lead.platform_id);
  const status = getStatusConfig(lead);
  const initials = (lead.name || '?')[0].toUpperCase();

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200 overflow-hidden">

      {/* ── Panel header ── */}
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

      {/* ── Scrollable body ── */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

        {/* Contact section */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Contact</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            <FieldRow icon={User} label="Nom" name="name" value={form.name} editing={editing} onChange={handle} />
            <FieldRow icon={Phone} label="Téléphone" name="phone_number" value={form.phone_number} editing={editing} onChange={handle} />
            <FieldRow icon={MapPin} label="Adresse" name="address" value={form.address} editing={editing} onChange={handle} />
          </div>
        </div>

        {/* Produit section */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Produit</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            {lead.product_id && (
              <FieldRow icon={Package} label="ID Produit" name="product_id" value={lead.product_id} editing={false} onChange={handle} />
            )}
            {lead.variation_id && (
              <FieldRow icon={Hash} label="Variation" name="variation_id" value={lead.variation_id} editing={false} onChange={handle} />
            )}
            <FieldRow icon={Package} label="Couleur" name="color" value={form.color} editing={editing} onChange={handle} />
            <FieldRow icon={Hash} label="Taille" name="size" value={form.size} editing={editing} onChange={handle} />
            <FieldRow icon={ShoppingBag} label="Quantité" name="quantity" value={form.quantity} type="number" editing={editing} onChange={handle} />
          </div>
        </div>

        {/* Commande section */}
        {lead.pending_order_reference && (
          <div>
            <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Commande</h3>
            <div className="bg-gray-50 rounded-2xl px-4">
              <FieldRow icon={ShoppingBag} label="Référence" name="ref" value={lead.pending_order_reference} editing={false} onChange={() => { }} />
              {lead.pending_order_created_at && (
                <FieldRow icon={Clock} label="Date" name="date"
                  value={new Date(lead.pending_order_created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' })}
                  editing={false} onChange={() => { }} />
              )}
            </div>
          </div>
        )}

        {/* Identifiants */}
        <div>
          <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-2">Identifiants</h3>
          <div className="bg-gray-50 rounded-2xl px-4">
            <FieldRow icon={Hash} label="ID Lead" name="id" value={`#${lead.id}`} editing={false} onChange={() => { }} />
            <FieldRow icon={MessageCircle} label="Platform ID" name="platform_id" value={lead.platform_id} editing={false} onChange={() => { }} />
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>
        )}
      </div>

      {/* ── Footer actions ── */}
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

/* ─── Main page ──────────────────────────────────────────────────── */
const Leads = () => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState('all');
  const [selected, setSelected] = useState(new Set());
  const [panelLead, setPanelLead] = useState(null);   // currently open in detail panel
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await fetchLeads(SHOP_ID, p > 1 ? p : undefined);
      setLeads(data.results || data);
      setTotal(data.count || (data.results || data).length);
    } catch {
      setError('Impossible de charger les leads.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(page); }, [load, page]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return leads.filter(l => {
      const matchSearch = !q ||
        l.name?.toLowerCase().includes(q) ||
        l.platform_id?.toLowerCase().includes(q) ||
        l.phone_number?.includes(q) ||
        l.address?.toLowerCase().includes(q);
      return matchSearch && matchTab(l, activeTab);
    });
  }, [leads, search, activeTab]);

  const tabCounts = useMemo(() => {
    const counts = {};
    TABS.forEach(t => { counts[t.key] = leads.filter(l => matchTab(l, t.key)).length; });
    return counts;
  }, [leads]);

  const allSelected = filtered.length > 0 && filtered.every(l => selected.has(l.id));
  const toggleAll = () => {
    if (allSelected) setSelected(prev => { const s = new Set(prev); filtered.forEach(l => s.delete(l.id)); return s; });
    else setSelected(prev => { const s = new Set(prev); filtered.forEach(l => s.add(l.id)); return s; });
  };
  const toggleOne = (id) => setSelected(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const handleSaved = (updated) => {
    setLeads(prev => prev.map(l => l.id === updated.id ? updated : l));
    setPanelLead(updated);
  };

  const [confirmingId, setConfirmingId] = useState(null);
  const handleConfirm = async (lead) => {
    setConfirmingId(lead.id);
    try {
      const updated = await updateLead(lead.id, {
        has_pending_order: false,
        agent_confirmation_pending: false,
      });
      setLeads(prev => prev.map(l => l.id === updated.id ? updated : l));
      if (panelLead?.id === updated.id) setPanelLead(updated);
    } catch (e) {
      console.error('Confirm failed', e);
    } finally {
      setConfirmingId(null);
    }
  };

  const [menuOpen, setMenuOpen] = useState(null); // lead.id or null

  const handleDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteLead(toDelete.id);
      setLeads(prev => prev.filter(l => l.id !== toDelete.id));
      setTotal(t => t - 1);
      if (panelLead?.id === toDelete.id) setPanelLead(null);
      setToDelete(null);
    } catch {
      setDeleting(false);
    } finally {
      setDeleting(false);
    }
  };

  const panelOpen = !!panelLead;

  return (
    <div className="h-full flex flex-col bg-[#f5f7fa] overflow-hidden relative">

      {/* ── Top Header ── */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Leads</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              {total} prospect{total !== 1 ? 's' : ''} au total
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => load(page)}
              className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Actualiser
            </button>
            <button className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <MoreVertical className="w-4 h-4" />
              Actions
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors shadow-sm">
              <Plus className="w-4 h-4" />
              Nouveau lead
            </button>
          </div>
        </div>

        {/* Status tabs */}
        <div className="flex items-center gap-0 px-6 overflow-x-auto">
          {TABS.map(tab => {
            const isActive = activeTab === tab.key;
            const count = tabCounts[tab.key] ?? 0;
            return (
              <button key={tab.key}
                onClick={() => { setActiveTab(tab.key); setSelected(new Set()); }}
                className={`relative flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-all ${isActive ? 'border-[#0f6885] text-[#0f6885]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200'
                  }`}>
                {tab.label}
                <span className={`inline-flex items-center justify-center min-w-[22px] h-5 px-1.5 rounded-full text-[11px] font-bold ${isActive ? 'bg-[#0f6885] text-white' : 'bg-gray-100 text-gray-600'
                  }`}>{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Search bar ── */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 max-w-sm focus-within:border-[#0f6885] transition-colors">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher (nom, téléphone, adresse…)"
              className="bg-transparent text-sm text-gray-700 placeholder-gray-400 border-0 focus:outline-none w-full" />
            {search && (
              <button onClick={() => setSearch('')}><X className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600" /></button>
            )}
          </div>
          {selected.size > 0 && (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-gray-500 font-medium">{selected.size} sélectionné{selected.size > 1 ? 's' : ''}</span>
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors">
                <Trash2 className="w-3.5 h-3.5" />
                Supprimer
              </button>
            </div>
          )}
        </div>
      </div>


      {/* ── Body ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Table — shrinks when panel is open */}
        <div style={panelOpen ? { marginRight: '620px' } : {}} className="flex-1 flex flex-col overflow-hidden transition-all duration-300">
          <div className="flex-1 overflow-auto">
            {error ? (
              <div className="flex flex-col items-center justify-center h-full gap-5 px-6 py-16">
                <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center">
                  <WifiOff className="w-8 h-8 text-red-400" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-700 mb-1">Impossible de charger les leads</p>
                  <p className="text-xs text-gray-400 max-w-xs">{error}</p>
                </div>
                <button onClick={() => load(page)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors">
                  <RefreshCw className="w-4 h-4" /> Réessayer
                </button>
              </div>
            ) : loading && leads.length === 0 ? (
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 z-10 bg-white border-b border-gray-200">
                  <tr>
                    <th className="w-10 pl-6 py-3" />
                    {['CLIENT', 'PLATEFORME', 'CONTACT', 'PRODUIT', 'STATUT'].map(h => (
                      <th key={h} className="text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-4 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {Array.from({ length: 7 }).map((_, i) => (
                    <tr key={i} className="bg-white">
                      <td className="pl-6 py-3.5"><div className="w-4 h-4 bg-gray-100 rounded animate-pulse" /></td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse" />
                          <div className="space-y-1.5">
                            <div className="h-3 w-24 bg-gray-200 rounded-full animate-pulse" />
                            <div className="h-2.5 w-14 bg-gray-100 rounded-full animate-pulse" />
                          </div>
                        </div>
                      </td>
                      {[80, 100, 90, 70].map((w, j) => (
                        <td key={j} className="px-4 py-3.5">
                          <div className="h-3 bg-gray-100 rounded-full animate-pulse" style={{ width: w }} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : leads.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-5 px-6 py-16">
                <div className="w-20 h-20 rounded-3xl bg-[#eef6f9] flex items-center justify-center">
                  <Users className="w-10 h-10 text-[#0f6885]/40" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-700 mb-1">Aucun lead pour le moment</p>
                  <p className="text-xs text-gray-400 max-w-xs leading-relaxed">
                    Les prospects détectés par le bot apparaîtront ici dès qu'une conversation démarrera.
                  </p>
                </div>
                <button onClick={() => load(1)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#0f6885] bg-[#eef6f9] hover:bg-[#dceef5] rounded-xl transition-colors">
                  <RefreshCw className="w-3.5 h-3.5" /> Actualiser
                </button>
              </div>
            ) : (
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 z-10 bg-white border-b border-gray-200">
                  <tr>
                    <th className="w-10 pl-6 py-3">
                      <input type="checkbox" checked={allSelected} onChange={toggleAll}
                        className="w-4 h-4 rounded border-gray-300 cursor-pointer accent-[#0f6885]" />
                    </th>
                    {['CLIENT', 'PLATEFORME', 'TÉL. / ADRESSE', 'PRODUIT', 'STATUT'].map(h => (
                      <th key={h} className="text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-4 py-3 whitespace-nowrap">{h}</th>
                    ))}
                    <th className="text-center text-[11px] font-bold text-gray-400 uppercase tracking-wider px-4 py-3 whitespace-nowrap">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.length === 0 ? (
                    <tr><td colSpan={6}>
                      <div className="flex flex-col items-center justify-center gap-4 py-16">
                        <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center">
                          <SearchX className="w-7 h-7 text-gray-400" />
                        </div>
                        <div className="text-center">
                          <p className="text-sm font-semibold text-gray-600 mb-1">Aucun résultat pour « {search} »</p>
                          <p className="text-xs text-gray-400">Essayez un autre nom, téléphone ou adresse.</p>
                        </div>
                        <button onClick={() => setSearch('')}
                          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors">
                          <X className="w-3.5 h-3.5" /> Effacer la recherche
                        </button>
                      </div>
                    </td></tr>
                  ) : filtered.map((lead) => {
                    const { label: platLabel, color: platColor } = getPlatformInfo(lead.platform_id);
                    const status = getStatusConfig(lead);
                    const isChecked = selected.has(lead.id);
                    const isActive = panelLead?.id === lead.id;
                    return (
                      <tr key={lead.id}
                        onClick={() => setPanelLead(isActive ? null : lead)}
                        className={`group transition-colors cursor-pointer ${isActive ? 'bg-[#eef6f9] border-l-2 border-l-[#0f6885]' :
                          isChecked ? 'bg-[#f5fafc]' : 'bg-white hover:bg-gray-50'
                          }`}>
                        <td className="pl-6 py-3.5" onClick={e => e.stopPropagation()}>
                          <input type="checkbox" checked={isChecked} onChange={() => toggleOne(lead.id)}
                            className="w-4 h-4 rounded border-gray-300 cursor-pointer accent-[#0f6885]" />
                        </td>

                        {/* Client */}
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-[#0f6885]' : 'bg-[#0f6885]/10'}`}>
                              <span className={`text-xs font-bold ${isActive ? 'text-white' : 'text-[#0f6885]'}`}>
                                {(lead.name || '?')[0].toUpperCase()}
                              </span>
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-gray-800 leading-tight truncate max-w-[110px]">{lead.name || '—'}</p>
                              <p className="text-[11px] text-gray-400">#{lead.id}</p>
                            </div>
                          </div>
                        </td>

                        {/* Platform */}
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold ${platColor}`}>
                            {platLabel}
                          </span>
                        </td>

                        {/* Contact */}
                        <td className="px-4 py-3.5">
                          {lead.phone_number ? (
                            <div className="flex items-center gap-1.5 text-xs text-gray-700 font-semibold">
                              <Phone className="w-3 h-3 text-gray-400 flex-shrink-0" />
                              {lead.phone_number}
                            </div>
                          ) : null}
                          {lead.address ? (
                            <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5">
                              <MapPin className="w-3 h-3 text-gray-400 flex-shrink-0" />
                              <span className="truncate max-w-[120px]">{lead.address}</span>
                            </div>
                          ) : null}
                          {!lead.phone_number && !lead.address && <span className="text-xs text-gray-300">—</span>}
                        </td>

                        {/* Product */}
                        <td className="px-4 py-3.5">
                          {lead.product_id ? (
                            <div className="text-xs font-mono font-semibold text-[#0f6885]">{lead.product_id}</div>
                          ) : null}
                          {(lead.color || lead.size) ? (
                            <div className="text-xs text-gray-500 mt-0.5">
                              {[lead.color, lead.size].filter(Boolean).join(' · ')}
                            </div>
                          ) : null}
                          {!lead.product_id && !lead.color && !lead.size && <span className="text-xs text-gray-300">—</span>}
                        </td>

                        {/* Status */}
                        <td className="px-4 py-3.5">
                          <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${status.color}`}>
                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${status.dot}`} />
                            {status.label}
                          </div>
                        </td>

                        {/* 3-dots Actions menu */}
                        <td className="px-1 py-3.5 text-right" onClick={e => e.stopPropagation()}>
                          <div className="relative inline-block">
                            <button
                              onClick={() => setMenuOpen(menuOpen === lead.id ? null : lead.id)}
                              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>

                            {menuOpen === lead.id && (
                              <div className="absolute right-0 top-8 z-50 w-44 bg-white border border-gray-200 rounded-xl shadow-lg py-1 text-sm">
                                {/* Voir */}
                                <button
                                  onClick={() => { setMenuOpen(null); setPanelLead(lead); }}
                                  className="w-full flex items-center gap-3 px-4 py-1.5 text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                  <User className="w-3.5 h-3.5 text-gray-400" /> Voir détails
                                </button>
                                {/* Modifier */}
                                <button
                                  onClick={() => { setMenuOpen(null); setPanelLead(lead); }}
                                  className="w-full flex items-center gap-3 px-4 py-1.5 text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                  <Edit3 className="w-3.5 h-3.5 text-gray-400" /> Modifier
                                </button>
                                {/* Confirmer — only for pending */}
                                {(lead.has_pending_order || lead.agent_confirmation_pending) && (
                                  <button
                                    onClick={() => { setMenuOpen(null); handleConfirm(lead); }}
                                    disabled={confirmingId === lead.id}
                                    className="w-full flex items-center gap-3 px-4 py-1.5 text-emerald-700 hover:bg-emerald-50 transition-colors disabled:opacity-50"
                                  >
                                    <CheckCircle className="w-3.5 h-3.5" />
                                    {confirmingId === lead.id ? 'Confirmation…' : 'Confirmer'}
                                  </button>
                                )}
                                <div className="border-t border-gray-100 my-1" />
                                {/* Supprimer */}
                                <button
                                  onClick={() => { setMenuOpen(null); setToDelete(lead); }}
                                  className="w-full flex items-center gap-3 px-4 py-1.5 text-red-600 hover:bg-red-50 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" /> Supprimer
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex-shrink-0 flex items-center justify-between px-6 py-3 bg-white border-t border-gray-200">
              <p className="text-xs text-gray-500">
                {filtered.length} affichés · Page {page} / {totalPages}
              </p>
              <div className="flex items-center gap-1.5">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                  className="p-1.5 text-gray-400 hover:text-[#0f6885] hover:bg-[#eef6f9] rounded-lg transition-colors disabled:opacity-30">
                  <ChevronLeft className="w-4 h-4" />
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
                  const p = start + i;
                  return (
                    <button key={p} onClick={() => setPage(p)}
                      className={`w-7 h-7 rounded-lg text-xs font-semibold transition-colors ${p === page ? 'bg-[#0f6885] text-white' : 'text-gray-500 hover:bg-gray-100'}`}>
                      {p}
                    </button>
                  );
                })}
                <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                  className="p-1.5 text-gray-400 hover:text-[#0f6885] hover:bg-[#eef6f9] rounded-lg transition-colors disabled:opacity-30">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* ── Slide-in panel — full page height ── */}
      <div
        style={{ width: '620px' }}
        className={`absolute top-0 right-0 h-full z-20 shadow-2xl transition-transform duration-300 ease-in-out ${panelOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {panelLead && (
          <LeadPanel
            lead={panelLead}
            onClose={() => setPanelLead(null)}
            onSaved={handleSaved}
            onDelete={(lead) => setToDelete(lead)}
          />
        )}
      </div>

      {/* Delete modal */}
      {toDelete && (
        <DeleteModal
          lead={toDelete}
          deleting={deleting}
          onClose={() => setToDelete(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
};

export default Leads;
