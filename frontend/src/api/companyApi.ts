import axios from 'axios';
import { getAccessToken } from '../providers/AuthProvider';

const API_BASE = process.env.REACT_APP_CRM_API_URL || 'http://localhost:8000/api/v1/crm';

const companyApi = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

companyApi.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export interface CompanySettings {
  shop_id: string;
  name: string;
  response_mode: 'nlu' | 'llm';
  llm_context: string | null;
  has_gemini_key: boolean;
  has_llm_context: boolean;
  is_active: boolean;
}

/** GET /api/v1/crm/company/{shopId}/ */
export const getCompanySettings = async (shopId: string): Promise<CompanySettings> => {
  const { data } = await companyApi.get<CompanySettings>(`/company/${shopId}/`);
  return data;
};

/** PATCH /api/v1/crm/company/{shopId}/ */
export const updateCompanySettings = async (
  shopId: string,
  patch: Partial<{
    response_mode: string;
    gemini_api_key: string;
    llm_context: string;
  }>
): Promise<CompanySettings> => {
  const { data } = await companyApi.patch<CompanySettings>(`/company/${shopId}/`, patch);
  return data;
};
