import React, { useState } from 'react';
import {
  Phone, MapPin,
  User, Edit3, CheckCircle, Trash2, MoreVertical, SearchX, X,
} from 'lucide-react';
import type { Lead, LeadStatus } from '../../types';
import { getPlatformInfo } from '../../utils/leads';
import StatusBadgeSelect from './StatusBadgeSelect';

interface LeadTableProps {
  leads: Lead[];
  loading: boolean;
  selected: Set<number>;
  toggleAll: () => void;
  toggleOne: (id: number) => void;
  allSelected: boolean;
  panelLeadId: number | null;
  onRowClick: (lead: Lead) => void;
  onStatusChange: (lead: Lead, value: LeadStatus) => void;
  onConfirm: (lead: Lead) => void;
  onDelete: (lead: Lead) => void;
  onOpenPanel: (lead: Lead) => void;
  changingStatusId: number | null;
  confirmingId: number | null;
  search: string;
  onClearSearch: () => void;
}

const LeadTable: React.FC<LeadTableProps> = ({
  leads, loading, selected, toggleAll, toggleOne, allSelected,
  panelLeadId, onRowClick, onStatusChange, onConfirm, onDelete, onOpenPanel,
  changingStatusId, confirmingId, search, onClearSearch,
}) => {
  const [menuOpen, setMenuOpen] = useState<number | null>(null);

  // Skeleton loader
  if (loading && leads.length === 0) {
    return (
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-sm border-collapse min-w-[600px]">
          <thead className="sticky top-0 z-10 bg-white border-b border-gray-200">
            <tr>
              <th className="w-10 pl-4 sm:pl-6 py-3" />
              {['CLIENT', 'PLATEFORME', 'CONTACT', 'PRODUIT', 'STATUT'].map((h) => (
                <th key={h} className="text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {Array.from({ length: 7 }).map((_, i) => (
              <tr key={i} className="bg-white">
                <td className="pl-4 sm:pl-6 py-3.5">
                  <div className="w-4 h-4 bg-gray-100 rounded animate-pulse" />
                </td>
                <td className="px-3 sm:px-4 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse flex-shrink-0" />
                    <div className="space-y-1.5">
                      <div className="h-3 w-20 bg-gray-200 rounded-full animate-pulse" />
                      <div className="h-2.5 w-12 bg-gray-100 rounded-full animate-pulse" />
                    </div>
                  </div>
                </td>
                {[80, 100, 90, 70].map((w, j) => (
                  <td key={j} className="px-3 sm:px-4 py-3.5">
                    <div className="h-3 bg-gray-100 rounded-full animate-pulse" style={{ width: w }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // No results
  if (leads.length === 0 && search) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 py-16 px-6">
        <div className="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center">
          <SearchX className="w-7 h-7 text-gray-400" />
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold text-gray-600 mb-1">Aucun résultat pour « {search} »</p>
          <p className="text-xs text-gray-400">Essayez un autre nom, téléphone ou adresse.</p>
        </div>
        <button
          onClick={onClearSearch}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
        >
          <X className="w-3.5 h-3.5" /> Effacer la recherche
        </button>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full text-sm border-collapse min-w-[560px]">
        <thead className="sticky top-0 z-10 bg-white border-b border-gray-200">
          <tr>
            <th className="w-10 pl-4 sm:pl-6 py-3">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                className="w-4 h-4 rounded border-gray-300 cursor-pointer accent-[#0f6885]"
              />
            </th>
            <th className="text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">CLIENT</th>
            {/* Hidden on mobile */}
            <th className="hidden sm:table-cell text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">PLATEFORME</th>
            <th className="hidden md:table-cell text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">TÉL. / ADRESSE</th>
            <th className="hidden md:table-cell text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">PRODUIT</th>
            <th className="text-left text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">STATUT</th>
            <th className="text-center text-[11px] font-bold text-gray-400 uppercase tracking-wider px-3 sm:px-4 py-3 whitespace-nowrap">ACTIONS</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.map((lead) => {
            const { label: platLabel, color: platColor } = getPlatformInfo(lead.platform_id);
            const isChecked = selected.has(lead.id);
            const isActive = panelLeadId === lead.id;
            return (
              <tr
                key={lead.id}
                onClick={() => onRowClick(lead)}
                className={`group transition-colors cursor-pointer ${
                  isActive ? 'bg-[#eef6f9] border-l-2 border-l-[#0f6885]' :
                  isChecked ? 'bg-[#f5fafc]' : 'bg-white hover:bg-gray-50'
                }`}
              >
                {/* Checkbox */}
                <td className="pl-4 sm:pl-6 py-3.5" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleOne(lead.id)}
                    className="w-4 h-4 rounded border-gray-300 cursor-pointer accent-[#0f6885]"
                  />
                </td>

                {/* Client */}
                <td className="px-3 sm:px-4 py-3.5">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-[#0f6885]' : 'bg-[#0f6885]/10'}`}>
                      <span className={`text-xs font-bold ${isActive ? 'text-white' : 'text-[#0f6885]'}`}>
                        {(lead.name || '?')[0].toUpperCase()}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-gray-800 leading-tight truncate max-w-[90px] sm:max-w-[120px]">
                        {lead.name || '—'}
                      </p>
                      <p className="text-[11px] text-gray-400">#{lead.id}</p>
                    </div>
                  </div>
                </td>

                {/* Platform — hidden on mobile */}
                <td className="hidden sm:table-cell px-3 sm:px-4 py-3.5">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-[11px] font-bold ${platColor}`}>
                    {platLabel}
                  </span>
                </td>

                {/* Contact — hidden on mobile */}
                <td className="hidden md:table-cell px-3 sm:px-4 py-3.5">
                  {lead.phone_number ? (
                    <div className="flex items-center gap-1.5 text-xs text-gray-700 font-semibold">
                      <Phone className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      {lead.phone_number}
                    </div>
                  ) : null}
                  {lead.address ? (
                    <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5">
                      <MapPin className="w-3 h-3 text-gray-400 flex-shrink-0" />
                      <span className="truncate max-w-[110px]">{lead.address}</span>
                    </div>
                  ) : null}
                  {!lead.phone_number && !lead.address && <span className="text-xs text-gray-300">—</span>}
                </td>

                {/* Product — hidden on mobile */}
                <td className="hidden md:table-cell px-3 sm:px-4 py-3.5">
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
                <td className="px-3 sm:px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                  <StatusBadgeSelect
                    lead={lead}
                    loading={changingStatusId === lead.id}
                    onChange={(val) => onStatusChange(lead, val)}
                  />
                </td>

                {/* Actions menu */}
                <td className="px-1 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="relative inline-block">
                    <button
                      onClick={() => setMenuOpen(menuOpen === lead.id ? null : lead.id)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>

                    {menuOpen === lead.id && (
                      <div className="absolute right-0 top-8 z-50 w-44 bg-white border border-gray-200 rounded-xl shadow-lg py-1 text-sm">
                        <button
                          onClick={() => { setMenuOpen(null); onOpenPanel(lead); }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <User className="w-3.5 h-3.5 text-gray-400" /> Voir détails
                        </button>
                        <button
                          onClick={() => { setMenuOpen(null); onOpenPanel(lead); }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <Edit3 className="w-3.5 h-3.5 text-gray-400" /> Modifier
                        </button>
                        {(lead.has_pending_order || lead.agent_confirmation_pending) && (
                          <button
                            onClick={() => { setMenuOpen(null); onConfirm(lead); }}
                            disabled={confirmingId === lead.id}
                            className="w-full flex items-center gap-3 px-4 py-2 text-emerald-700 hover:bg-emerald-50 transition-colors disabled:opacity-50"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            {confirmingId === lead.id ? 'Confirmation…' : 'Confirmer'}
                          </button>
                        )}
                        <div className="border-t border-gray-100 my-1" />
                        <button
                          onClick={() => { setMenuOpen(null); onDelete(lead); }}
                          className="w-full flex items-center gap-3 px-4 py-2 text-red-600 hover:bg-red-50 transition-colors"
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
    </div>
  );
};

export default LeadTable;
