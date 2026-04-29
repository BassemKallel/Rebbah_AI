import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import {
  Search, RefreshCw, X,
  Users, TrendingUp, CheckCircle, WifiOff, Trash2, SlidersHorizontal, ChevronDown, Calendar,
} from 'lucide-react';
import type { Lead, LeadStatus } from '../../types';
import { STATUS_OPTIONS } from '../../constants/leads';
import { matchTab } from '../../utils/leads';
import { fetchLeads, patchLead as updateLeadApi, deleteLead as deleteLeadApi } from '../../api/crmApi';
import { getShopId } from '../../providers/AuthProvider';
import LeadTable from '../../components/leads/LeadTable';
import LeadPanel from '../../components/leads/LeadPanel';
import DeleteModal from '../../components/leads/DeleteModal';

/* ─── Tabs ───────────────────────────────────────────────────────── */
const TABS = [
  { key: 'all',       label: 'Tous',     fullLabel: 'Tous les leads', icon: Users,       color: 'text-[#0f6885]',   bg: 'bg-[#eef6f9]' },
  { key: 'engaged',   label: 'Engagé',   fullLabel: 'Engagés',        icon: TrendingUp,  color: 'text-amber-600',   bg: 'bg-amber-50' },
  { key: 'qualified', label: 'Qualifié', fullLabel: 'Qualifiés',       icon: CheckCircle, color: 'text-emerald-600', bg: 'bg-emerald-50' },
];

const PLATFORM_OPTIONS = [
  { value: '',          label: 'Toutes les plateformes', dot: '' },
  { value: 'messenger', label: 'Messenger',               dot: 'bg-blue-400' },
  { value: 'instagram', label: 'Instagram',               dot: 'bg-pink-400' },
  { value: 'poc',       label: 'POC / Test',              dot: 'bg-gray-400' },
];

/* ─── CustomSelect ───────────────────────────────────────────────── */
const CustomSelect: React.FC<{
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string; dot?: string }[];
  placeholder?: string;
}> = ({ value, onChange, options, placeholder }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const hasValue = !!value;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-all whitespace-nowrap ${
          hasValue
            ? 'border-[#0f6885] text-[#0f6885] bg-[#eef6f9]'
            : 'border-gray-200 text-gray-600 bg-white hover:bg-gray-50'
        }`}
      >
        {selected?.dot
          ? <span className={`w-2 h-2 rounded-full flex-shrink-0 ${selected.dot}`} />
          : <span className="w-2 h-2 rounded-full flex-shrink-0 border border-gray-300" />
        }
        <span>{selected?.label ?? placeholder ?? 'Sélectionner'}</span>
        {hasValue ? (
          <button type="button" onClick={(e) => { e.stopPropagation(); onChange(''); setOpen(false); }} className="ml-0.5">
            <X className="w-3 h-3 opacity-50 hover:opacity-100 transition-opacity" />
          </button>
        ) : (
          <ChevronDown className={`w-3.5 h-3.5 opacity-40 transition-transform ${open ? 'rotate-180' : ''}`} />
        )}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-50 bg-white border border-gray-100 rounded-xl shadow-xl py-1.5 min-w-[200px]">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => { onChange(o.value); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-sm transition-colors ${
                o.value === value ? 'bg-[#eef6f9] text-[#0f6885]' : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              {o.dot
                ? <span className={`w-2 h-2 rounded-full flex-shrink-0 ${o.dot}`} />
                : <span className="w-2 h-2 rounded-full flex-shrink-0 border border-gray-300" />
              }
              <span>{o.label}</span>
              {o.value === value && <span className="ml-auto text-[10px] text-[#0f6885]/50 font-medium">actif</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/* ─── DateRangePicker ────────────────────────────────────────────── */
const DateRangePicker: React.FC<{
  from: string;
  to: string;
  onFromChange: (v: string) => void;
  onToChange: (v: string) => void;
  onClear: () => void;
}> = ({ from, to, onFromChange, onToChange, onClear }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const fmt = (d: string) =>
    d ? new Date(d + 'T00:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }) : '';

  const hasValue = !!(from || to);
  const label = hasValue ? `${fmt(from) || '…'}  →  ${fmt(to) || '…'}` : 'Toute période';

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-all whitespace-nowrap ${
          hasValue
            ? 'border-[#0f6885] text-[#0f6885] bg-[#eef6f9]'
            : 'border-gray-200 text-gray-600 bg-white hover:bg-gray-50'
        }`}
      >
        <Calendar className="w-3.5 h-3.5 opacity-60 flex-shrink-0" />
        <span>{label}</span>
        {hasValue ? (
          <button type="button" onClick={(e) => { e.stopPropagation(); onClear(); }} className="ml-0.5">
            <X className="w-3 h-3 opacity-50 hover:opacity-100 transition-opacity" />
          </button>
        ) : (
          <ChevronDown className={`w-3.5 h-3.5 opacity-40 transition-transform ${open ? 'rotate-180' : ''}`} />
        )}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-50 bg-white border border-gray-100 rounded-xl shadow-xl p-4 w-[260px]">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">Plage de dates</p>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Du</label>
              <input
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => onFromChange(e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:border-[#0f6885] focus:ring-2 focus:ring-[#0f6885]/10 transition-colors"
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-px bg-gray-100" />
              <span className="text-[11px] text-gray-400 font-medium">à</span>
              <div className="flex-1 h-px bg-gray-100" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Au</label>
              <input
                type="date"
                value={to}
                min={from || undefined}
                onChange={(e) => onToChange(e.target.value)}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:border-[#0f6885] focus:ring-2 focus:ring-[#0f6885]/10 transition-colors"
              />
            </div>
          </div>
          {hasValue && (
            <button
              type="button"
              onClick={() => { onClear(); setOpen(false); }}
              className="mt-3 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <X className="w-3 h-3" /> Effacer les dates
            </button>
          )}
        </div>
      )}
    </div>
  );
};

/* ─── Main Page ─────────────────────────────────────────────────── */
const Leads: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [page] = useState(1);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState('all');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [panelLead, setPanelLead] = useState<Lead | null>(null);
  const [toDelete, setToDelete] = useState<Lead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [changingStatusId, setChangingStatusId] = useState<number | null>(null);

  /* ── Advanced filters ── */
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterPlatform, setFilterPlatform] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo]   = useState('');

  const activeFilterCount = [filterPlatform, filterDateFrom || filterDateTo].filter(Boolean).length;

  const load = useCallback(async (p: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const shopId = getShopId();
      const { data } = await fetchLeads(shopId);
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
      const matchPlatform = !filterPlatform ||
        l.platform_id?.toLowerCase().startsWith(filterPlatform);
      const matchFrom = !filterDateFrom || l.created_at >= filterDateFrom;
      const matchTo   = !filterDateTo   || l.created_at <= filterDateTo + 'T23:59:59';
      return matchSearch && matchPlatform && matchFrom && matchTo && matchTab(l, activeTab);
    });
  }, [leads, search, activeTab, filterPlatform, filterDateFrom, filterDateTo]);

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

  const clearFilters = () => { setFilterPlatform(''); setFilterDateFrom(''); setFilterDateTo(''); };

  /* ── Empty state config per tab ── */
  const currentTab = TABS.find((t) => t.key === activeTab) ?? TABS[0];
  const EMPTY_STATES: Record<string, { title: string; desc: string }> = {
    all:       { title: 'Aucun lead pour le moment',  desc: "Les leads sont créés automatiquement dès qu'une intention d'achat est détectée dans une conversation." },
    engaged:   { title: 'Aucun lead engagé',          desc: "Les leads ayant manifesté une intention d'achat apparaîtront ici." },
    qualified: { title: 'Aucun lead qualifié',        desc: "Une fois qu'une pré-commande est créée par le bot, le lead passe en statut Qualifié." },
  };
  const emptyState = EMPTY_STATES[activeTab] ?? EMPTY_STATES.all;

  const panelOpen = !!panelLead;

  return (
    <div className="h-full flex flex-col bg-[#f5f7fa] overflow-hidden relative">

      {/* ── Header ── */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-4">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Leads</h1>
            <p className="text-xs text-gray-400 mt-0.5">{total} lead{total !== 1 ? 's' : ''} au total</p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => load(page)}
              className="flex items-center gap-1.5 sm:gap-2 px-3 py-2 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden xs:inline">Actualiser</span>
            </button>
            <button
              onClick={() => setFiltersOpen((v) => !v)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 py-2 text-sm font-medium border rounded-xl transition-colors ${
                filtersOpen || activeFilterCount > 0
                  ? 'border-[#0f6885] text-[#0f6885] bg-[#eef6f9]'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              <span className="hidden xs:inline">Filtres</span>
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-[#0f6885] text-white text-[10px] font-bold">
                  {activeFilterCount}
                </span>
              )}
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${filtersOpen ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>

        {/* ── Advanced filters panel ── */}
        {filtersOpen && (
          <div className="px-4 sm:px-6 pb-4 pt-3 border-t border-gray-100 bg-[#f9fafb]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-gray-400 mr-1">Filtrer par :</span>
              <CustomSelect
                value={filterPlatform}
                onChange={setFilterPlatform}
                options={PLATFORM_OPTIONS}
                placeholder="Plateforme"
              />
              <DateRangePicker
                from={filterDateFrom}
                to={filterDateTo}
                onFromChange={setFilterDateFrom}
                onToChange={setFilterDateTo}
                onClear={() => { setFilterDateFrom(''); setFilterDateTo(''); }}
              />
              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-500 hover:text-red-600 hover:bg-red-50 rounded-xl border border-transparent transition-colors"
                >
                  <X className="w-3.5 h-3.5" /> Tout effacer
                </button>
              )}
            </div>
          </div>
        )}

        {/* Tabs — scrollable on mobile */}
        <div className="flex items-center px-4 sm:px-6 overflow-x-auto scrollbar-hide">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            const count = tabCounts[tab.key] ?? 0;
            return (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key); setSelected(new Set()); }}
                className={`relative flex items-center gap-2 px-3 sm:px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-all flex-shrink-0 ${
                  isActive ? 'border-[#0f6885] text-[#0f6885]' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200'
                }`}
              >
                <span className="hidden sm:inline">{tab.fullLabel}</span>
                <span className="sm:hidden">{tab.label}</span>
                <span className={`inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold ${
                  isActive ? 'bg-[#0f6885] text-white' : 'bg-gray-100 text-gray-600'
                }`}>
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Search bar ── */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 flex-1 max-w-sm focus-within:border-[#0f6885] transition-colors">
            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher par nom, téléphone…"
              className="bg-transparent text-sm text-gray-700 placeholder-gray-400 border-0 focus:outline-none w-full"
            />
            {search && (
              <button onClick={() => setSearch('')} aria-label="Effacer">
                <X className="w-3.5 h-3.5 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>
          {selected.size > 0 && (
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-gray-500 font-medium hidden sm:inline">
                {selected.size} sélectionné{selected.size > 1 ? 's' : ''}
              </span>
              <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors">
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden xs:inline">Supprimer</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table area — push right when panel is open on lg+ */}
        <div
          style={panelOpen ? { marginRight: 0 } : {}}
          className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${panelOpen ? 'lg:mr-[540px]' : ''}`}
        >
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
                <button
                  onClick={() => load(page)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-[#0f6885] hover:bg-[#0d5a72] rounded-xl transition-colors"
                >
                  <RefreshCw className="w-4 h-4" /> Réessayer
                </button>
              </div>
            ) : leads.length === 0 && !loading ? (
              /* ─── No leads at all (tab-specific) ─── */
              <div className="flex flex-col items-center justify-center h-full gap-6 px-6 py-16">
                <div className="relative flex items-center justify-center w-32 h-32">
                  <div className={`absolute inset-0 rounded-full ${currentTab.bg} opacity-20 scale-125`} />
                  <div className={`absolute inset-0 rounded-full ${currentTab.bg} opacity-40`} />
                  <div className={`relative w-28 h-28 rounded-full ${currentTab.bg} flex items-center justify-center`}>
                    <currentTab.icon className={`w-12 h-12 ${currentTab.color} opacity-75`} />
                  </div>
                </div>
                <div className="text-center max-w-xs">
                  <p className="text-base font-bold text-gray-800 mb-2">{emptyState.title}</p>
                  <p className="text-sm text-gray-400 leading-relaxed">{emptyState.desc}</p>
                </div>
                <button
                  onClick={() => load(1)}
                  className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-[#0f6885] bg-[#eef6f9] hover:bg-[#dceef5] rounded-xl transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Actualiser
                </button>
              </div>
            ) : filtered.length === 0 && !loading ? (
              /* ─── No results for active filters ─── */
              <div className="flex flex-col items-center justify-center h-full gap-5 px-6 py-16">
                <div className="w-20 h-20 rounded-3xl bg-gray-100 flex items-center justify-center">
                  <Search className="w-9 h-9 text-gray-300" />
                </div>
                <div className="text-center max-w-xs">
                  <p className="text-sm font-bold text-gray-700 mb-1.5">Aucun résultat</p>
                  <p className="text-xs text-gray-400 leading-relaxed">
                    Aucun lead ne correspond à votre recherche ou aux filtres actifs.
                  </p>
                </div>
                {/* Active filter chips */}
                <div className="flex flex-wrap justify-center gap-2">
                  {search && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                      Recherche&nbsp;: «&nbsp;{search}&nbsp;»
                      <button onClick={() => setSearch('')}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                  {filterPlatform && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#eef6f9] text-[#0f6885] text-xs rounded-full">
                      {PLATFORM_OPTIONS.find((o) => o.value === filterPlatform)?.label}
                      <button onClick={() => setFilterPlatform('')}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                  {(filterDateFrom || filterDateTo) && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#eef6f9] text-[#0f6885] text-xs rounded-full">
                      Période filtrée
                      <button onClick={() => { setFilterDateFrom(''); setFilterDateTo(''); }}><X className="w-3 h-3" /></button>
                    </span>
                  )}
                </div>
                <button
                  onClick={() => { setSearch(''); clearFilters(); }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 rounded-xl transition-colors"
                >
                  <X className="w-3.5 h-3.5" /> Effacer tout
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

        {/* ── Lead Panel ── */}
        {panelLead && (
          <div className="
            animate-slide-in-right
            fixed inset-0 z-30
            lg:absolute lg:inset-auto lg:right-0 lg:top-0 lg:bottom-0 lg:w-[540px]
          ">
            <LeadPanel
              lead={panelLead}
              onClose={() => setPanelLead(null)}
              onSaved={handleSaved}
              onDelete={setToDelete}
            />
          </div>
        )}
      </div>

      {/* ── Delete modal ── */}
      {toDelete && (
        <DeleteModal lead={toDelete} onClose={() => setToDelete(null)} onConfirm={handleDelete} deleting={deleting} />
      )}
    </div>
  );
};

export default Leads;
