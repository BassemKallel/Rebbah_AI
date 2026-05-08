import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Database, Search, Clock, FileText, Download, Upload, Loader2, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { mlopsApi } from '../../../api/mlopsApi';
import type { PaginatedManualDatasets } from '../../../types/mlops';

export default function ManualDatasetView() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClick = () => setShowExportMenu(false);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const { data, isLoading } = useQuery<PaginatedManualDatasets>({
    queryKey: ['manualDatasets', page, search],
    queryFn: () => mlopsApi.getManualDatasets({
      page,
      search: search || undefined
    })
  });

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    try {
      setUploading(true);
      const result = await mlopsApi.importDataset(file);
      toast.success(`Dataset importé ! ${result.imported} ajoutés, ${result.updated} mis à jour.`);
      queryClient.invalidateQueries({ queryKey: ['manualDatasets'] });
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
      const blob = await mlopsApi.exportDatasetBlob(format, true); // True to include ManualDataset
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Database className="w-6 h-6 text-[#0f6885]" />
            Données Manuelles
          </h2>
          <p className="text-gray-500 mt-1">
            Consultez les datasets importés ou annotés manuellement, isolés des erreurs de production.
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

      {/* Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm flex flex-col sm:flex-row gap-4 justify-between items-center">
        <div className="relative w-full sm:w-96">
          <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher par texte ou label..."
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0f6885]/20 focus:border-[#0f6885] transition-all"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-100 text-sm font-semibold text-gray-600">
                <th className="p-4 w-1/2">Texte Original</th>
                <th className="p-4">Label</th>
                <th className="p-4">Source</th>
                <th className="p-4 text-right">Date d'import</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-gray-500">
                    <div className="flex justify-center items-center gap-3">
                      <div className="w-5 h-5 border-2 border-[#0f6885] border-t-transparent rounded-full animate-spin" />
                      Chargement des données...
                    </div>
                  </td>
                </tr>
              ) : data?.results.length === 0 ? (
                <tr>
                  <td colSpan={4} className="p-12 text-center text-gray-500">
                    <Database className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-lg font-medium text-gray-900">Aucune donnée trouvée</p>
                    <p className="text-sm">Essayez de modifier votre recherche ou importez un nouveau dataset.</p>
                  </td>
                </tr>
              ) : (
                data?.results.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="p-4">
                      <p className="text-sm font-medium text-gray-900 break-words">{item.original_text}</p>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                        {item.label}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <FileText className="w-4 h-4" />
                        {item.source}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5 text-sm text-gray-500">
                        <Clock className="w-4 h-4" />
                        {new Date(item.created_at).toLocaleString('fr-FR', {
                          day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.count > 0 && (
          <div className="p-4 border-t border-gray-100 flex items-center justify-between bg-gray-50/50">
            <span className="text-sm text-gray-600">
              Total : <span className="font-semibold text-gray-900">{data.count}</span> entrées
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={!data.previous}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
              >
                Précédent
              </button>
              <span className="px-3 py-1.5 text-sm font-medium text-gray-700">
                Page {page}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.next}
                className="px-3 py-1.5 text-sm font-medium text-[#0f6885] bg-white border border-gray-200 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 transition-colors"
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
