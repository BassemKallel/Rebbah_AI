import api from './axiosInstance';
import { MLOpsStats, PaginatedFallbacks, RetrainingLog, RetrainingStatus } from '../types/mlops';

export const mlopsApi = {
  // 1. Dashboard Stats
  getStats: async (): Promise<MLOpsStats> => {
    const { data } = await api.get('/admin/mlops/stats/');
    return data;
  },

  // 2. Fallbacks Review List
  getFallbacks: async (params?: { 
    reviewed?: boolean; 
    trigger?: string; 
    intent?: string; 
    search?: string; 
    page?: number; 
    page_size?: number 
  }): Promise<PaginatedFallbacks> => {
    const { data } = await api.get('/admin/mlops/fallbacks/', { params });
    return data;
  },

  // 3. Review a Fallback
  reviewFallback: async (id: number, label: string): Promise<{ id: number; reviewed: boolean; review_label: string }> => {
    const { data } = await api.patch(`/admin/mlops/fallbacks/${id}/`, { review_label: label });
    return data;
  },

  // 4. Export Dataset
  exportDatasetUrl: (format: 'json' | 'csv' = 'json', reviewedOnly: boolean = true): string => {
    const baseUrl = api.defaults.baseURL || '';
    // Construction de l'URL pour le bouton <a> afin de trigger le téléchargement direct (n'oublie pas le token si nécessaire, mais on l'ajoute souvent par intercepteur. Mieux vaut utiliser un fetch blob pour les exports protégés)
    return `${baseUrl}/admin/mlops/export/?format=${format}&reviewed=${reviewedOnly}`;
  },

  exportDatasetBlob: async (format: 'json' | 'csv' = 'json', reviewedOnly: boolean = true): Promise<Blob> => {
    const { data } = await api.get('/admin/mlops/export/', {
      params: { format, reviewed: reviewedOnly },
      responseType: 'blob'
    });
    return data;
  },

  // 5. Retraining
  triggerRetrain: async (): Promise<{ message: string; log_id: number; samples: number }> => {
    const { data } = await api.post('/admin/mlops/retrain/trigger/');
    return data;
  },

  getRetrainStatus: async (): Promise<RetrainingStatus> => {
    const { data } = await api.get('/admin/mlops/retrain/status/');
    return data;
  },

  getRetrainReport: async (id: number): Promise<{ run_id: number; status: string; report: any }> => {
    const { data } = await api.get(`/admin/mlops/retrain/${id}/report/`);
    return data;
  }
};
