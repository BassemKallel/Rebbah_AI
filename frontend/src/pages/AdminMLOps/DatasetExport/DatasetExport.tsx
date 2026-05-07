import React, { useState } from 'react';
import { Download, FileJson, FileSpreadsheet, CheckCircle } from 'lucide-react';
import { mlopsApi } from '../../../api/mlopsApi';

export default function DatasetExport() {
  const [format, setFormat] = useState<'json' | 'csv'>('json');
  const [reviewedOnly, setReviewedOnly] = useState(true);
  const [downloading, setDownloading] = useState(false);

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

  return (
    <div className="max-w-4xl mx-auto flex flex-col h-full">
      <div className="mb-8 text-center">
        <h2 className="text-3xl font-extrabold text-gray-900">Export du Dataset</h2>
        <p className="text-gray-500 mt-3 max-w-2xl mx-auto">
          Téléchargez les données conversationnelles révisées pour entraîner vos propres modèles hors-ligne
          ou pour faire de l'analyse de données.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
        <div className="p-8">
          
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

        </div>
        
        {/* Helper footer */}
        <div className="bg-gray-50 p-6 text-sm text-gray-500 border-t border-gray-100 flex items-center gap-3">
          <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          Le pipeline CI/CD télécharge automatiquement ce dataset (version JSON) via l'API pour déclencher le réentraînement TunBERT.
        </div>
      </div>
    </div>
  );
}
