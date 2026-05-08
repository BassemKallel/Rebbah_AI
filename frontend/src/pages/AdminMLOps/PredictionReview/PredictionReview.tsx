import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, AlertCircle, Bot, Sparkles, Edit3, Download, Upload, Loader2, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { mlopsApi } from '../../../api/mlopsApi';
import type { NLUFallbackLog, PaginatedFallbacks } from '../../../types/mlops';

const INTENT_GROUPS = [
  {
    label: 'Questions',
    options: ['ASK_ADVICE', 'ASK_AVAILABILITY', 'ASK_DELIVERY', 'ASK_DETAILS', 'ASK_DISCOUNT', 'ASK_LOCATION', 'ASK_PRICE']
  },
  {
    label: 'Commandes',
    options: ['ORDER_PRODUCT', 'CANCEL_ORDER', 'TRACK_ORDER', 'CHECK_PACKAGE', 'ECHANGE']
  },
  {
    label: 'Général',
    options: ['GREETING', 'CONFIRM_DENY', 'COMPLAINT', 'INFORM_INFO', 'NOISE']
  }
];

export default function PredictionReview() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<'ALL' | 'PENDING' | 'REVIEWED'>('PENDING');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  
  // local state for inline editing
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  
  useEffect(() => {
    const handleClick = () => setShowExportMenu(false);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const { data, isLoading } = useQuery<PaginatedFallbacks>({
    queryKey: ['fallbacks', filter, page, search],
    queryFn: () => mlopsApi.getFallbacks({
      reviewed: filter === 'PENDING' ? false : filter === 'REVIEWED' ? true : undefined,
      page,
      search: search || undefined
    })
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, label }: { id: number; label: string }) => mlopsApi.reviewFallback(id, label),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fallbacks'] });
      setEditingId(null);
      toast.success('Label validé avec succès !');
    },
    onError: () => {
      toast.error('Erreur lors de la validation du label.');
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

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      setUploading(true);
      const result = await mlopsApi.importDataset(file);
      toast.success(`Dataset importé ! ${result.imported} ajoutés, ${result.updated} mis à jour.`);
      queryClient.invalidateQueries({ queryKey: ['fallbacks'] });
    } catch (error: any) {
      console.error('Import failed', error);
      toast.error(error.response?.data?.error || 'Erreur lors de l\'import');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDownloadBlob = async (format: 'json' | 'csv') => {
    try {
      setDownloading(true);
      const blob = await mlopsApi.exportDatasetBlob(format, true);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tiktak_dataset_${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success(`Dataset exporté en ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Download failed', error);
      toast.error('Erreur lors du téléchargement');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Révision des Labels</h2>
          <p className="text-gray-500 mt-1">
            Corrigez les prédictions échouées (fallbacks) pour améliorer le dataset d'entraînement.
          </p>
        </div>
        
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <input 
            type="file" 
            accept=".json,.csv" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={handleImport} 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm disabled:opacity-50"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            Importer
          </button>
          
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              disabled={downloading}
              className="flex items-center gap-2 px-4 py-2 bg-[#0f6885] text-white rounded-lg hover:bg-[#0c536a] transition-colors font-medium text-sm disabled:opacity-50"
            >
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Exporter
              <ChevronDown className="w-4 h-4" />
            </button>
            
            {showExportMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-gray-100 rounded-xl shadow-lg z-50 overflow-hidden animate-fade-in-up">
                <button 
                  onClick={() => { setShowExportMenu(false); handleDownloadBlob('json'); }}
                  className="w-full text-left px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 hover:text-[#0f6885] font-medium border-b border-gray-50 transition-colors"
                >
                  Exporter en JSON
                </button>
                <button 
                  onClick={() => { setShowExportMenu(false); handleDownloadBlob('csv'); }}
                  className="w-full text-left px-4 py-3 text-sm text-gray-700 hover:bg-gray-50 hover:text-[#0f6885] font-medium transition-colors"
                >
                  Exporter en CSV
                </button>
              </div>
            )}
          </div>
        </div>
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
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-3 bg-gray-50 p-2 rounded-lg border border-gray-100">
                          <Bot className="w-4 h-4 text-gray-500 flex-shrink-0" />
                          <div className="flex-1 flex justify-between items-center">
                            <span className="text-sm font-semibold text-gray-700">{log.tunbert_intent}</span>
                            <span className="text-xs font-mono text-gray-400">{(log.tunbert_confidence * 100).toFixed(1)}%</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 bg-[#0f6885]/5 p-2 rounded-lg border border-[#0f6885]/10">
                          <Sparkles className="w-4 h-4 text-[#0f6885] flex-shrink-0" />
                          <div className="flex-1 flex justify-between items-center">
                            <span className="text-sm font-semibold text-[#0f6885]">{log.gemini_intent}</span>
                            {log.gemini_confidence && <span className="text-xs font-mono text-[#0f6885]/70">{(log.gemini_confidence * 100).toFixed(1)}%</span>}
                          </div>
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
                            {INTENT_GROUPS.map(group => (
                              <optgroup key={group.label} label={group.label}>
                                {group.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                              </optgroup>
                            ))}
                          </select>
                          <button
                            onClick={() => handleSave(log.id)}
                            disabled={reviewMutation.isPending}
                            className="bg-[#0f6885] text-white p-1.5 rounded-lg hover:bg-[#0c5168]"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between group">
                          <div className="flex items-center gap-2">
                            {log.reviewed ? (
                              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                <CheckCircle className="w-4 h-4" />
                                <span className="text-sm font-bold">{log.review_label}</span>
                              </div>
                            ) : (
                              <div className="bg-orange-50 border border-orange-200 text-orange-600 px-3 py-1.5 rounded-lg flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" />
                                <span className="text-sm font-medium">Non révisé</span>
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => handleEditClick(log)}
                            className="p-2 text-gray-400 hover:text-[#0f6885] hover:bg-[#0f6885]/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                            title="Modifier le label"
                          >
                            <Edit3 className="w-4 h-4" />
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
