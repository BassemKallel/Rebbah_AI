import React, { useState, useMemo, useCallback } from 'react';
import {
  Search, RefreshCw, X, Plus, MoreVertical,
  Users, Clock, CheckCircle, AlertCircle, WifiOff, Trash2,
} from 'lucide-react';
import type { Lead, LeadStatus } from '../../types';
import { SHOP_ID, PAGE_SIZE } from '../../constants';
import { STATUS_OPTIONS } from '../../constants/leads';
import { matchTab } from '../../utils/leads';
import { fetchLeads, patchLead as updateLeadApi, deleteLead as deleteLeadApi } from '../../api/crmApi';
import LeadTable from '../../components/leads/LeadTable';
import LeadPanel from '../../components/leads/LeadPanel';
import DeleteModal from '../../components/leads/DeleteModal';

/* ─── Tabs ──────────────────────────────────────────────────────── */
const TABS = [
  { key: 'all', label: 'Tous les leads', icon: Users },
  { key: 'pending', label: 'En attente', icon: Clock },
  { key: 'confirmed', label: 'Confirmés', icon: CheckCircle },
  { key: 'agent', label: 'Confirmation agent', icon: AlertCircle },
];

/* ─── Main Page ─────────────────────────────────────────────────── */
const Leads: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState('all');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [panelLead, setPanelLead] = useState<Lead | null>(null);
  const [toDelete, setToDelete] = useState<Lead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [changingStatusId, setChangingStatusId] = useState<number | null>(null);

  const load = useCallback(async (p: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await fetchLeads(SHOP_ID);
      setLeads(data.results || data);
      setTotal(data.count || (data.results || data).length);
    } catch {
      setError('Impossible de charger les leads.');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { load(page); }, [load, page]);

  /* ── Filtering ── */
  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return leads.filter((l) => {
      const matchSearch = !q ||
        l.name?.toLowerCase().includes(q) ||
        l.platform_id?.toLowerCase().includes(q) ||
        l.phone_number?.includes(q) ||
        l.address?.toLowerCase().includes(q);
      return matchSearch && matchTab(l, activeTab);
    });
  }, [leads, search, activeTab]);

  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    TABS.forEach((t) => { counts[t.key] = leads.filter((l) => matchTab(l, t.key)).length; });
    return counts;
  }, [leads]);

  /* ── Selection ── */
  const allSelected = filtered.length > 0 && filtered.every((l) => selected.has(l.id));
  const toggleAll = () => {
    if (allSelected) setSelected((prev) => { const s = new Set(prev); filtered.forEach((l) => s.delete(l.id)); return s; });
    else setSelected((prev) => { const s = new Set(prev); filtered.forEach((l) => s.add(l.id)); return s; });
  };
  const toggleOne = (id: number) => setSelected((prev) => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  /* ── Actions ── */
  const handleSaved = (updated: Lead) => {
    setLeads((prev) => prev.map((l) => l.id === updated.id ? updated : l));
    setPanelLead(updated);
  };

  const handleConfirm = async (lead: Lead) => {
    setConfirmingId(lead.id);
    try {
      const { data: updated } = await updateLeadApi(lead.id, { has_pending_order: false, agent_confirmation_pending: false });
      setLeads((prev) => prev.map((l) => l.id === updated.id ? updated : l));
      if (panelLead?.id === updated.id) setPanelLead(updated);
    } catch (e) { console.error('Confirm failed', e); }
    finally { setConfirmingId(null); }
  };

  const handleStatusChange = async (lead: Lead, statusValue: LeadStatus) => {
    const opt = STATUS_OPTIONS.find((o) => o.value === statusValue);
    if (!opt) return;
    setChangingStatusId(lead.id);
    try {
      const { data: updated } = await updateLeadApi(lead.id, { has_pending_order: opt.has_pending_order, agent_confirmation_pending: opt.agent_confirmation_pending });
      setLeads((prev) => prev.map((l) => l.id === updated.id ? updated : l));
      if (panelLead?.id === updated.id) setPanelLead(updated);
    } catch (e) { console.error('Status change failed', e); }
    finally { setChangingStatusId(null); }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteLeadApi(toDelete.id);
      setLeads((prev) => prev.filter((l) => l.id !== toDelete.id));
      setTotal((t) => t - 1);
      if (panelLead?.id === toDelete.id) setPanelLead(null);
      setToDelete(null);
    } finally { setDeleting(false); }
  };

  const panelOpen = !!panelLead;

  return (
    <div className="h-full flex flex-col bg-[#f5f7fa] overflow-hidden relative">

      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Leads</h1>
            <p className="text-xs text-gray-400 mt-0.5">{total} prospect{total !== 1 ? 's' : ''} au total</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => load(page)} className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Actualiser
            </button>
            <button className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <MoreVertical className="w-4 h-4" /> Actions
            </button>
            <button className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors shadow-sm">
              <Plus className="w-4 h-4" /> Nouveau lead
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-0 px-6 overflow-x-auto">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            const count = tabCounts[tab.key] ?? 0;
            return (
              <button key={tab.key}
                onClick={() => { setActiveTab(tab.key); setSelected(new Set()); }}
                className={`relative flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-all ${isActive ? 'border-[#0f6885] text-[#0f6885]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200'}`}>
                {tab.label}
                <span className={`inline-flex items-center justify-center min-w-[22px] h-5 px-1.5 rounded-full text-[11px] font-bold ${isActive ? 'bg-[#0f6885] text-white' : 'bg-gray-100 text-gray-600'}`}>{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Search */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 max-w-sm focus-within:border-[#0f6885] transition-colors">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher (nom, téléphone, adresse…)"
              className="bg-transparent text-sm text-gray-700 placeholder-gray-400 border-0 focus:outline-none w-full" />
            {search && <button onClick={() => setSearch('')}><X className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600" /></button>}
          </div>
          {selected.size > 0 && (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-gray-500 font-medium">{selected.size} sélectionné{selected.size > 1 ? 's' : ''}</span>
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors">
                <Trash2 className="w-3.5 h-3.5" /> Supprimer
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        <div style={panelOpen ? { marginRight: '620px' } : {}} className="flex-1 flex flex-col overflow-hidden transition-all duration-300">
          <div className="flex-1 overflow-auto">
            {error ? (
              <div className="flex flex-col items-center justify-center h-full gap-5 px-6 py-16">
                <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center"><WifiOff className="w-8 h-8 text-red-400" /></div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-700 mb-1">Impossible de charger les leads</p>
                  <p className="text-xs text-gray-400 max-w-xs">{error}</p>
                </div>
                <button onClick={() => load(page)} className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors">
                  <RefreshCw className="w-4 h-4" /> Réessayer
                </button>
              </div>
            ) : leads.length === 0 && !loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-5 px-6 py-16">
                <div className="w-20 h-20 rounded-3xl bg-[#eef6f9] flex items-center justify-center"><Users className="w-10 h-10 text-[#0f6885]/40" /></div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-700 mb-1">Aucun lead pour le moment</p>
                  <p className="text-xs text-gray-400 max-w-xs leading-relaxed">Les prospects détectés par le bot apparaîtront ici dès qu'une conversation démarrera.</p>
                </div>
                <button onClick={() => load(1)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#0f6885] bg-[#eef6f9] hover:bg-[#dceef5] rounded-xl transition-colors">
                  <RefreshCw className="w-3.5 h-3.5" /> Actualiser
                </button>
              </div>
            ) : (
              <LeadTable
                leads={filtered}
                loading={loading}
                selected={selected}
                toggleAll={toggleAll}
                toggleOne={toggleOne}
                allSelected={allSelected}
                panelLeadId={panelLead?.id ?? null}
                onRowClick={(lead) => setPanelLead(panelLead?.id === lead.id ? null : lead)}
                onStatusChange={handleStatusChange}
                onConfirm={handleConfirm}
                onDelete={setToDelete}
                onOpenPanel={setPanelLead}
                changingStatusId={changingStatusId}
                confirmingId={confirmingId}
                search={search}
                onClearSearch={() => setSearch('')}
              />
            )}
          </div>
        </div>

        {/* Panel */}
        {panelLead && (
          <div className="absolute right-0 top-0 bottom-0 w-[620px] z-20">
            <LeadPanel
              lead={panelLead}
              onClose={() => setPanelLead(null)}
              onSaved={handleSaved}
              onDelete={setToDelete}
            />
          </div>
        )}
      </div>

      {/* Delete modal */}
      {toDelete && (
        <DeleteModal lead={toDelete} onClose={() => setToDelete(null)} onConfirm={handleDelete} deleting={deleting} />
      )}
    </div>
  );
};

export default Leads;
