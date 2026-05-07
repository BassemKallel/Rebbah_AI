import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, RotateCw, CheckCircle, XCircle, AlertTriangle, Activity } from 'lucide-react';
import { mlopsApi } from '../../../api/mlopsApi';
import { LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';

export default function Retraining() {
  const queryClient = useQueryClient();
  const [selectedRun, setSelectedRun] = useState<number | null>(null);

  // Poll status every 10 seconds
  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ['retrain-status'],
    queryFn: mlopsApi.getRetrainStatus,
    refetchInterval: 10000,
  });

  const { data: statsData } = useQuery({
    queryKey: ['mlops-stats'],
    queryFn: mlopsApi.getStats,
  });

  const triggerMutation = useMutation({
    mutationFn: mlopsApi.triggerRetrain,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retrain-status'] });
      alert('Réentraînement déclenché avec succès via GitHub Actions.');
    },
    onError: (err: any) => {
      alert(err.response?.data?.error || 'Erreur lors du déclenchement');
    }
  });

  const { data: reportData, isLoading: reportLoading } = useQuery({
    queryKey: ['retrain-report', selectedRun],
    queryFn: () => mlopsApi.getRetrainReport(selectedRun!),
    enabled: !!selectedRun,
  });

  const currentRun = statusData?.current;
  const isRunning = currentRun?.status === 'PENDING' || currentRun?.status === 'RUNNING';
  const readySamples = statsData?.reviewed_count || 0;

  useEffect(() => {
    if (statusData?.history && statusData.history.length > 0 && !selectedRun) {
      // Auto-select latest run if it has a report
      const latestWithReport = statusData.history.find(h => h.status === 'SUCCESS' || h.status === 'SKIPPED');
      if (latestWithReport) setSelectedRun(latestWithReport.id);
    }
  }, [statusData, selectedRun]);

  return (
    <div className="max-w-[1600px] mx-auto flex flex-col h-full space-y-6">
      
      {/* Header & Trigger */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 flex flex-wrap justify-between items-center gap-6 bg-gradient-to-br from-white to-gray-50/50">
        <div>
          <h2 className="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-[#0f6885] to-indigo-600">
            Pipeline de Réentraînement
          </h2>
          <p className="text-gray-500 mt-2 font-medium">
            Déclenchez le réentraînement TunBERT via GitHub Actions ou consultez les rapports des anciens runs.
          </p>
        </div>

        <div className="flex items-center gap-6 bg-gray-50 p-4 rounded-xl border border-gray-100">
          <div className="text-center">
            <div className="text-3xl font-extrabold text-[#0f6885]">{readySamples}</div>
            <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mt-1">Exemples validés</div>
          </div>
          
          <div className="w-px h-12 bg-gray-200"></div>
          
          <div className="flex flex-col gap-2">
            <button
              onClick={() => triggerMutation.mutate()}
              disabled={isRunning || readySamples < 50}
              className={`flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg font-bold text-white transition-all ${
                isRunning 
                  ? 'bg-gray-400 cursor-not-allowed'
                  : readySamples < 50
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-[#0f6885] hover:bg-[#0c5168] shadow-md hover:shadow-lg'
              }`}
            >
              {isRunning ? (
                <RotateCw className="w-5 h-5 animate-spin" />
              ) : (
                <Play className="w-5 h-5" />
              )}
              {isRunning ? 'En cours...' : 'Lancer l\'entraînement'}
            </button>
            {readySamples < 50 && !isRunning && (
              <span className="text-xs text-orange-500 font-medium text-center">
                Min. 50 exemples requis (encore {50 - readySamples})
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 flex-1">
        {/* Left Col: History list */}
        <div className="xl:col-span-1 bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-gray-100 bg-gray-50">
            <h3 className="font-bold text-gray-900 uppercase tracking-wider text-sm">Historique des runs</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2 max-h-[600px]">
            {statusLoading ? (
              <div className="p-4 text-center text-gray-400">Chargement...</div>
            ) : statusData?.history.length === 0 ? (
              <div className="p-4 text-center text-gray-400">Aucun run trouvé.</div>
            ) : (
              statusData?.history.map((run) => (
                <button
                  key={run.id}
                  onClick={() => setSelectedRun(run.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    selectedRun === run.id 
                      ? 'border-[#0f6885] bg-[#0f6885]/5 shadow-sm' 
                      : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <span className="font-extrabold text-gray-900">Run #{run.run_number || run.id}</span>
                    <span className={`px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-lg border ${
                      run.status === 'SUCCESS' ? 'bg-emerald-50 border-emerald-200 text-emerald-700' :
                      run.status === 'FAILED' ? 'bg-red-50 border-red-200 text-red-700' :
                      run.status === 'SKIPPED' ? 'bg-orange-50 border-orange-200 text-orange-700' :
                      'bg-blue-50 border-blue-200 text-blue-700'
                    }`}>
                      {run.status}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 flex items-center justify-between font-medium">
                    <span>{new Date(run.started_at).toLocaleString('fr-FR')}</span>
                    {run.f1_improvement !== null && (
                      <span className={`font-bold px-2 py-1 rounded-md ${run.f1_improvement > 0 ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'}`}>
                        Δ {run.f1_improvement > 0 ? '+' : ''}{run.f1_improvement.toFixed(4)}
                      </span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Col: Report Details */}
        <div className="xl:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          {!selectedRun ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <Activity className="w-12 h-12 mb-4 opacity-20" />
              <p>Sélectionnez un run pour voir le rapport détaillé.</p>
            </div>
          ) : reportLoading ? (
            <div className="h-full flex items-center justify-center">
              <div className="w-8 h-8 border-4 border-[#0f6885] border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : reportData?.report ? (
            <div className="space-y-8 animate-fade-in">
              {/* Header Report */}
              <div className="flex justify-between items-end border-b border-gray-100 pb-6">
                <div>
                  <h3 className="text-2xl font-extrabold text-gray-900">Rapport d'entraînement</h3>
                  <div className="flex flex-wrap gap-3 mt-3 text-sm">
                    <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-md font-medium">Durée : {reportData.report.meta.duration_seconds}s</span>
                    <span className="bg-gray-100 text-gray-600 px-3 py-1 rounded-md font-medium">Epochs : {reportData.report.meta.epochs}</span>
                    <span className="bg-[#0f6885]/10 text-[#0f6885] px-3 py-1 rounded-md font-bold">Modèle : {reportData.report.meta.base_model}</span>
                  </div>
                </div>
                {reportData.deployed ? (
                  <div className="flex items-center gap-2 text-emerald-700 bg-emerald-50 border border-emerald-200 px-4 py-2 rounded-xl font-bold shadow-sm">
                    <CheckCircle className="w-5 h-5" />
                    Déployé en production
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-orange-700 bg-orange-50 border border-orange-200 px-4 py-2 rounded-xl font-bold shadow-sm">
                    <AlertTriangle className="w-5 h-5" />
                    Non déployé (Skip)
                  </div>
                )}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <div className="text-gray-500 text-sm font-semibold mb-1">F1 Weighted (Nouveau)</div>
                  <div className="text-3xl font-extrabold text-gray-900">
                    {(reportData.report.evaluation.new_model.f1_weighted * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <div className="text-gray-500 text-sm font-semibold mb-1">F1 Macro</div>
                  <div className="text-3xl font-extrabold text-gray-900">
                    {(reportData.report.evaluation.new_model.f1_macro * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <div className="text-gray-500 text-sm font-semibold mb-1">Accuracy</div>
                  <div className="text-3xl font-extrabold text-gray-900">
                    {(reportData.report.evaluation.new_model.accuracy * 100).toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Learning Curves */}
              <div>
                <h4 className="font-bold text-gray-900 mb-4">Courbes d'apprentissage</h4>
                <div className="h-64 border border-gray-100 rounded-xl p-4 bg-gray-50/50">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={reportData.report.training_curves}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis dataKey="epoch" tick={{fontSize: 12}} />
                      <YAxis yAxisId="left" tick={{fontSize: 12}} domain={['auto', 'auto']} />
                      <YAxis yAxisId="right" orientation="right" tick={{fontSize: 12}} domain={[0, 1]} />
                      <RechartsTooltip />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="train_loss" stroke="#ef4444" strokeWidth={2} name="Train Loss" />
                      <Line yAxisId="left" type="monotone" dataKey="val_loss" stroke="#f97316" strokeWidth={2} name="Val Loss" />
                      <Line yAxisId="right" type="monotone" dataKey="val_f1" stroke="#0f6885" strokeWidth={2} name="Val F1" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Per class metrics */}
              <div>
                <h4 className="font-bold text-gray-900 mb-4">Performances par classe (Top 10)</h4>
                <div className="overflow-x-auto border border-gray-200 rounded-xl">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-gray-500">
                      <tr>
                        <th className="px-4 py-3 font-semibold">Intent</th>
                        <th className="px-4 py-3 font-semibold">F1-Score</th>
                        <th className="px-4 py-3 font-semibold">Precision</th>
                        <th className="px-4 py-3 font-semibold">Support</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {reportData.report.evaluation.per_class
                        .sort((a: any, b: any) => b.support - a.support)
                        .slice(0, 10)
                        .map((c: any) => (
                        <tr key={c.intent}>
                          <td className="px-4 py-2 font-medium">{c.intent}</td>
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2">
                              <span className="w-8">{(c.f1 * 100).toFixed(1)}</span>
                              <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-[#0f6885]" style={{ width: `${c.f1 * 100}%` }}></div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-2">{(c.precision * 100).toFixed(1)}%</td>
                          <td className="px-4 py-2 text-gray-500">{c.support}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <XCircle className="w-12 h-12 mb-4 opacity-20" />
              <p>Erreur ou rapport non trouvé pour ce run.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
