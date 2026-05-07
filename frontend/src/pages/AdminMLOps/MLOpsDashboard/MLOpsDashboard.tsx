import React, { useEffect, useState } from 'react';
import { Database, AlertTriangle, Activity, BrainCircuit, Server, CheckCircle2, XCircle } from 'lucide-react';
import { greeting, todayFormatted } from '../../../utils/date';
import KpiCard from '../../../components/dashboard/KpiCard';
import type { KpiData } from '../../../types';
import { mlopsApi } from '../../../api/mlopsApi';
import type { MLOpsStats, ModelsHealthResponse } from '../../../types/mlops';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, AreaChart, Area, CartesianGrid } from 'recharts';

export default function MLOpsDashboard() {
  const [stats, setStats] = useState<MLOpsStats | null>(null);
  const [health, setHealth] = useState<ModelsHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      mlopsApi.getStats(),
      mlopsApi.getModelsHealth().catch(e => {
        console.error("Health check failed", e);
        return null;
      })
    ])
      .then(([statsData, healthData]) => {
        setStats(statsData);
        if (healthData) setHealth(healthData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  const kpiCards: KpiData[] = stats ? [
    {
      label: 'Fallbacks (30j)', value: String(stats.total_fallbacks_30d),
      delta: '', up: true, sub: 'Messages non compris',
      icon: <AlertTriangle className="w-5 h-5" />,
      bg: 'bg-orange-50', text: 'text-orange-600', sparkline: stats.sparkline_7d,
    },
    {
      label: 'À Réviser', value: String(stats.pending_review),
      delta: '', up: false, sub: 'En attente',
      icon: <Database className="w-5 h-5" />,
      bg: 'bg-red-50', text: 'text-red-600', sparkline: [0,0,0],
    },
    {
      label: 'Dataset (Validé)', value: String(stats.reviewed_count),
      delta: stats.reviewed_count >= 50 ? 'Prêt' : 'Incomplet', up: stats.reviewed_count >= 50, sub: 'Exemples TunBERT',
      icon: <BrainCircuit className="w-5 h-5" />,
      bg: 'bg-blue-50', text: 'text-blue-600', sparkline: [0,0,0],
    },
    {
      label: 'Confiance Moyenne', value: `${(stats.avg_tunbert_confidence * 100).toFixed(1)}%`,
      delta: '', up: true, sub: 'Derniers 30 jours',
      icon: <Activity className="w-5 h-5" />,
      bg: 'bg-emerald-50', text: 'text-emerald-600', sparkline: [0,0,0],
    },
  ] : [];

  return (
    <div className="min-h-full bg-gray-50 pb-8">
      {/* Greeting */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 sm:mb-7">
        <div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900">{greeting()}, Admin MLOps</h2>
          <p className="text-sm text-gray-400 mt-0.5 capitalize">{todayFormatted()}</p>
        </div>
        <div className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-white border border-gray-200 rounded-xl shadow-sm flex-shrink-0">
          <BrainCircuit className="w-4 h-4 text-[#0f6885]" />
          <span className="text-sm font-medium text-gray-700">TunBERT</span>
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#0f6885]">
             v3 (Active)
          </span>
        </div>
      </div>

      {/* Health Cards */}
      {health && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-5 mb-6 sm:mb-7">
          {[
            { id: 'tunbert', name: 'TunBERT', icon: <BrainCircuit className="w-6 h-6" />, data: health.tunbert, bg: 'bg-indigo-50', text: 'text-indigo-600' },
            { id: 'gliner', name: 'GLiNER', icon: <Database className="w-6 h-6" />, data: health.gliner, bg: 'bg-purple-50', text: 'text-purple-600' },
            { id: 'clip', name: 'CLIP Vision', icon: <Server className="w-6 h-6" />, data: health.clip, bg: 'bg-cyan-50', text: 'text-cyan-600' },
          ].map(model => (
            <div key={model.id} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${model.bg} ${model.text}`}>
                  {model.icon}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-gray-900">{model.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">{model.data.version}</p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                {model.data.status === 'healthy' ? (
                  <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full text-xs font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" /> En ligne
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-red-600 bg-red-50 px-2 py-1 rounded-full text-xs font-semibold">
                    <XCircle className="w-3.5 h-3.5" /> Hors ligne
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 sm:gap-5 mb-6 sm:mb-7">
        {kpiCards.map((k) => <KpiCard key={k.label} k={k} />)}
      </div>

      {/* Charts / Data */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 sm:gap-6">
        
        {/* Fallbacks History Chart */}
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Historique des Fallbacks (7j)</h3>
          <div className="h-64">
            {stats && stats.sparkline_7d.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={stats.sparkline_7d.map((val, i) => ({ day: `J-${6-i}`, count: val }))}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0f6885" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#0f6885" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                  <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Area type="monotone" dataKey="count" stroke="#0f6885" strokeWidth={3} fillOpacity={1} fill="url(#colorCount)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
               <div className="flex items-center justify-center h-full text-gray-400">Aucune donnée disponible</div>
            )}
          </div>
        </div>

        {/* Reasons Chart */}
        <div className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Raisons des Fallbacks (30j)</h3>
          <div className="h-64">
            {stats && stats.fallback_by_reason.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.fallback_by_reason}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="count"
                    nameKey="trigger_reason"
                    label={({ payload, percent }: any) => `${payload.trigger_reason} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {stats.fallback_by_reason.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={['#ef4444', '#f97316', '#eab308', '#3b82f6', '#8b5cf6'][index % 5]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
               <div className="flex items-center justify-center h-full text-gray-400">Aucune donnée disponible</div>
            )}
          </div>
        </div>

        {/* Retraining Status */}
        <div className="lg:col-span-2 bg-white border border-gray-100 rounded-2xl p-5 shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Dernier Entraînement</h3>
          {stats?.last_retraining ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b pb-3 border-gray-100">
                <span className="text-gray-500">Statut</span>
                <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${
                  stats.last_retraining.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-700' :
                  stats.last_retraining.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                  stats.last_retraining.status === 'SKIPPED' ? 'bg-orange-100 text-orange-700' :
                  'bg-blue-100 text-blue-700'
                }`}>
                  {stats.last_retraining.status}
                </span>
              </div>
              <div className="flex justify-between items-center border-b pb-3 border-gray-100">
                <span className="text-gray-500">Date</span>
                <span className="font-medium">{new Date(stats.last_retraining.started_at).toLocaleString('fr-FR')}</span>
              </div>
              <div className="flex justify-between items-center border-b pb-3 border-gray-100">
                <span className="text-gray-500">Ancien F1-Score</span>
                <span className="font-medium">{stats.last_retraining.old_f1 ?? 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center border-b pb-3 border-gray-100">
                <span className="text-gray-500">Nouveau F1-Score</span>
                <span className="font-medium">{stats.last_retraining.new_f1 ?? 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-500">Amélioration</span>
                <span className={`font-bold ${stats.last_retraining.f1_improvement && stats.last_retraining.f1_improvement > 0 ? 'text-emerald-500' : 'text-gray-500'}`}>
                  {stats.last_retraining.f1_improvement && stats.last_retraining.f1_improvement > 0 ? '+' : ''}{stats.last_retraining.f1_improvement ?? '0'}
                </span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400">Aucun historique d'entraînement</div>
          )}
        </div>

      </div>
    </div>
  );
}
