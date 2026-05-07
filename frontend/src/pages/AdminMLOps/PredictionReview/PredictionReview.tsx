import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { mlopsApi } from '../../../api/mlopsApi';
import type { NLUFallbackLog } from '../../../types/mlops';

const INTENT_OPTIONS = [
  'ASK_ADVICE', 'ASK_AVAILABILITY', 'ASK_DELIVERY', 'ASK_DETAILS',
  'ASK_DISCOUNT', 'ASK_LOCATION', 'ASK_PRICE', 'CANCEL_ORDER',
  'CHECK_PACKAGE', 'COMPLAINT', 'CONFIRM_DENY', 'ECHANGE',
  'GREETING', 'INFORM_INFO', 'NOISE', 'ORDER_PRODUCT', 'TRACK_ORDER',
];

export default function PredictionReview() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'REVIEWED'>('PENDING');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  
  // local state for inline editing
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['fallbacks', filter, page, search],
    queryFn: () => mlopsApi.getFallbacks({
      reviewed: filter === 'PENDING' ? false : filter === 'REVIEWED' ? true : undefined,
      page,
      search: search || undefined
    }),
    keepPreviousData: true,
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, label }: { id: number; label: string }) => mlopsApi.reviewFallback(id, label),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fallbacks'] });
      setEditingId(null);
    }
  });

  const handleSave = (id: number) => {
    if (!editValue) return;
    reviewMutation.mutate({ id, label: editValue });
  };

  const handleEditClick = (log: NLUFallbackLog) => {
    setEditingId(log.id);
    setEditValue(log.review_label || log.gemini_intent || '');
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Révision des Labels</h2>
        <p className="text-gray-500 mt-1">
          Corrigez les prédictions échouées (fallbacks) pour améliorer le dataset d'entraînement.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col flex-1">
        {/* Toolbar */}
        <div className="p-4 border-b border-gray-200 flex flex-wrap gap-4 justify-between items-center bg-gray-50/50">
          <div className="flex gap-2">
            {(['PENDING', 'REVIEWED', 'ALL'] as const).map(f => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1); }}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === f 
                    ? 'bg-[#0f6885] text-white' 
                    : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
                }`}
              >
                {f === 'PENDING' ? 'À réviser' : f === 'REVIEWED' ? 'Validés' : 'Tous'}
              </button>
            ))}
          </div>
          
          <div className="relative">
            <input
              type="text"
              placeholder="Rechercher dans les messages..."
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#0f6885]/20 focus:border-[#0f6885] w-64"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
            <div className="absolute left-3 top-2.5 text-gray-400">
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500">
                <th className="px-6 py-4 font-semibold">Message Original</th>
                <th className="px-6 py-4 font-semibold">Erreur (TunBERT / Gemini)</th>
                <th className="px-6 py-4 font-semibold w-64">Label Validé</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr><td colSpan={3} className="px-6 py-8 text-center text-gray-400">Chargement...</td></tr>
              ) : data?.results.length === 0 ? (
                <tr><td colSpan={3} className="px-6 py-8 text-center text-gray-500">Aucun log trouvé.</td></tr>
              ) : (
                data?.results.map((log) => (
                  <tr key={log.id} className={`hover:bg-gray-50/50 transition-colors ${log.reviewed ? 'bg-emerald-50/30' : ''}`}>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 font-medium break-words max-w-md">
                        "{log.original_text}"
                      </div>
                      <div className="text-xs text-gray-400 mt-1 flex items-center gap-2">
                        <span>{new Date(log.created_at).toLocaleString('fr-FR')}</span>
                        <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">{log.trigger_reason}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase font-bold text-gray-400 w-16">TunBERT</span>
                          <span className="text-sm bg-red-50 text-red-700 px-2 py-0.5 rounded">{log.tunbert_intent}</span>
                          <span className="text-xs text-gray-400">{(log.tunbert_confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase font-bold text-gray-400 w-16">Gemini</span>
                          <span className="text-sm bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{log.gemini_intent}</span>
                          {log.gemini_confidence && <span className="text-xs text-gray-400">{(log.gemini_confidence * 100).toFixed(1)}%</span>}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {editingId === log.id ? (
                        <div className="flex items-center gap-2">
                          <select
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:ring-[#0f6885]"
                          >
                            <option value="">Sélectionner...</option>
                            {INTENT_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                          </select>
                          <button
                            onClick={() => handleSave(log.id)}
                            disabled={reviewMutation.isLoading}
                            className="bg-[#0f6885] text-white p-1.5 rounded-lg hover:bg-[#0c5168]"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between group">
                          <div className="flex items-center gap-2">
                            {log.reviewed ? (
                              <>
                                <CheckCircle className="w-4 h-4 text-emerald-500" />
                                <span className="text-sm font-semibold text-emerald-700">{log.review_label}</span>
                              </>
                            ) : (
                              <>
                                <AlertCircle className="w-4 h-4 text-orange-400" />
                                <span className="text-sm text-orange-600 font-medium">Non révisé</span>
                              </>
                            )}
                          </div>
                          <button
                            onClick={() => handleEditClick(log)}
                            className="text-gray-400 hover:text-[#0f6885] opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            Éditer
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.count > 0 && (
          <div className="p-4 border-t border-gray-200 flex justify-between items-center text-sm text-gray-600">
            <div>
              Affichage {((page - 1) * 20) + 1} - {Math.min(page * 20, data.count)} sur {data.count}
            </div>
            <div className="flex gap-2">
              <button
                disabled={!data.previous}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Précédent
              </button>
              <button
                disabled={!data.next}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Suivant
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
