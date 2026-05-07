import React, { useState } from 'react';
import { Download, FileJson, FileSpreadsheet, CheckCircle, Upload, FileUp } from 'lucide-react';
import { mlopsApi } from '../../../api/mlopsApi';

export default function DatasetExport() {
  const [activeTab, setActiveTab] = useState<'export' | 'import'>('export');
  const [format, setFormat] = useState<'json' | 'csv'>('json');
  const [reviewedOnly, setReviewedOnly] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<{ message: string; imported: number; updated: number } | null>(null);

  const handleDownloadBlob = async () => {
    try {
      setDownloading(true);
      const blob = await mlopsApi.exportDatasetBlob(format, reviewedOnly);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tiktak_dataset_${new Date().toISOString().split('T')[0]}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (error) {
      console.error('Download failed', error);
      alert('Erreur lors du téléchargement');
    } finally {
      setDownloading(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    try {
      setUploading(true);
      setImportResult(null);
      const result = await mlopsApi.importDataset(importFile);
      setImportResult(result);
      setImportFile(null);
    } catch (error: any) {
      console.error('Import failed', error);
      alert(error.response?.data?.error || 'Erreur lors de l import du fichier');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-full">
      <div className="mb-8 text-center">
        <h2 className="text-3xl sm:text-4xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-[#0f6885] to-indigo-600 pb-1">
          Gestion de Dataset
        </h2>
        <p className="text-gray-500 mt-4 max-w-2xl mx-auto font-medium">
          Exportez ou importez des données conversationnelles pour entraîner vos propres modèles hors-ligne ou restaurer des annotations.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex bg-gray-100 p-1 rounded-xl mb-8 max-w-md mx-auto shadow-inner">
        <button
          onClick={() => setActiveTab('export')}
          className={`flex-1 py-2.5 text-sm font-bold text-center transition-all rounded-lg ${
            activeTab === 'export' ? 'bg-white text-[#0f6885] shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Exporter
        </button>
        <button
          onClick={() => setActiveTab('import')}
          className={`flex-1 py-2.5 text-sm font-bold text-center transition-all rounded-lg ${
            activeTab === 'import' ? 'bg-white text-[#0f6885] shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Importer
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="p-8">
          
          {activeTab === 'export' ? (
            <>
              {/* Format Selection */}
              <div className="mb-8">
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Format de fichier</h3>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setFormat('json')}
                    className={`p-4 border-2 rounded-xl flex items-center gap-4 transition-all ${
                      format === 'json' ? 'border-[#0f6885] bg-[#0f6885]/5 ring-2 ring-[#0f6885]/20' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className={`p-3 rounded-lg ${format === 'json' ? 'bg-[#0f6885] text-white' : 'bg-gray-100 text-gray-500'}`}>
                      <FileJson className="w-6 h-6" />
                    </div>
                    <div className="text-left">
                      <div className={`font-bold ${format === 'json' ? 'text-[#0f6885]' : 'text-gray-900'}`}>JSON (HuggingFace)</div>
                      <div className="text-sm text-gray-500">Format idéal pour le fine-tuning TunBERT</div>
                    </div>
                    {format === 'json' && <CheckCircle className="w-5 h-5 text-[#0f6885] ml-auto" />}
                  </button>

                  <button
                    onClick={() => setFormat('csv')}
                    className={`p-4 border-2 rounded-xl flex items-center gap-4 transition-all ${
                      format === 'csv' ? 'border-emerald-600 bg-emerald-50 ring-2 ring-emerald-500/20' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className={`p-3 rounded-lg ${format === 'csv' ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
                      <FileSpreadsheet className="w-6 h-6" />
                    </div>
                    <div className="text-left">
                      <div className={`font-bold ${format === 'csv' ? 'text-emerald-700' : 'text-gray-900'}`}>CSV (Excel/Pandas)</div>
                      <div className="text-sm text-gray-500">Idéal pour l'analyse et la visualisation</div>
                    </div>
                    {format === 'csv' && <CheckCircle className="w-5 h-5 text-emerald-600 ml-auto" />}
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="mb-10">
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Données à inclure</h3>
                <label className="flex items-start gap-4 p-4 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors">
                  <div className="mt-0.5">
                    <input
                      type="checkbox"
                      checked={reviewedOnly}
                      onChange={(e) => setReviewedOnly(e.target.checked)}
                      className="w-5 h-5 text-[#0f6885] border-gray-300 rounded focus:ring-[#0f6885]"
                    />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">Exemples validés uniquement</div>
                    <div className="text-sm text-gray-500 mt-1">
                      Ne télécharge que les logs de fallback qui ont été révisés manuellement par l'administrateur.
                      Recommandé pour garantir la qualité du dataset d'entraînement.
                    </div>
                  </div>
                </label>
              </div>

              {/* Action */}
              <div className="border-t border-gray-100 pt-8 flex justify-center">
                <button
                  onClick={handleDownloadBlob}
                  disabled={downloading}
                  className={`flex items-center gap-3 px-8 py-4 rounded-xl font-bold text-white shadow-lg transition-all transform hover:-translate-y-0.5 active:translate-y-0 ${
                    format === 'json' 
                      ? 'bg-[#0f6885] hover:bg-[#0c5168] shadow-[#0f6885]/25' 
                      : 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-600/25'
                  } ${downloading ? 'opacity-75 cursor-wait' : ''}`}
                >
                  {downloading ? (
                    <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Download className="w-6 h-6" />
                  )}
                  {downloading ? 'Préparation en cours...' : `Télécharger le Dataset (.${format})`}
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Import UI */}
              <div className="mb-10">
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-4">Uploader un fichier</h3>
                <div 
                  className={`border-2 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center text-center transition-all cursor-pointer ${
                    importFile 
                      ? 'border-[#0f6885] bg-[#0f6885]/5 shadow-inner' 
                      : 'border-gray-300 hover:border-[#0f6885] hover:bg-gray-50'
                  }`}
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  <div className={`p-4 rounded-full mb-5 ${importFile ? 'bg-[#0f6885] text-white' : 'bg-gray-100 text-gray-400'}`}>
                    {importFile ? <CheckCircle className="w-8 h-8" /> : <FileUp className="w-8 h-8" />}
                  </div>
                  <p className="text-xl font-bold text-gray-900 mb-2">
                    {importFile ? importFile.name : 'Cliquez pour sélectionner un fichier JSON'}
                  </p>
                  <p className="text-sm font-medium text-gray-500">
                    {importFile ? `${(importFile.size / 1024).toFixed(2)} KB prês pour l'import` : 'Format JSON exporté par l\'outil MLOps TikTak'}
                  </p>
                  <input 
                    id="file-upload" 
                    type="file" 
                    accept=".json" 
                    className="hidden" 
                    onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>

              {importResult && (
                <div className="mb-8 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-bold">{importResult.message}</div>
                    <div className="text-sm mt-1">
                      {importResult.imported} nouveaux logs importés, {importResult.updated} logs mis à jour.
                    </div>
                  </div>
                </div>
              )}

              <div className="border-t border-gray-100 pt-8 flex justify-center">
                <button
                  onClick={handleImport}
                  disabled={uploading || !importFile}
                  className={`flex items-center gap-3 px-8 py-4 rounded-xl font-bold text-white shadow-lg transition-all ${
                    !importFile ? 'bg-gray-300 cursor-not-allowed' : 'bg-[#0f6885] hover:bg-[#0c5168] hover:-translate-y-0.5 shadow-[#0f6885]/25'
                  } ${uploading ? 'opacity-75 cursor-wait' : ''}`}
                >
                  {uploading ? (
                    <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    <Upload className="w-6 h-6" />
                  )}
                  {uploading ? 'Importation en cours...' : 'Lancer l\'import'}
                </button>
              </div>
            </>
          )}

        </div>
        
        {/* Helper footer */}
        <div className="bg-gray-50 p-6 text-sm text-gray-500 border-t border-gray-100 flex items-center gap-3">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          {activeTab === 'export' 
            ? 'Le pipeline CI/CD télécharge automatiquement ce dataset (version JSON) via l\'API pour déclencher le réentraînement TunBERT.'
            : 'L\'import permet de restaurer ou de fusionner des annotations faites hors-ligne dans la base de données.'}
        </div>
      </div>
    </div>
  );
}
