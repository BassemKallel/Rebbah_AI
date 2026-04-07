import api from './axiosInstance';

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
  const { data } = await api.get<CompanySettings>(`/api/v1/crm/company/${shopId}/`);
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
  const { data } = await api.patch<CompanySettings>(`/api/v1/crm/company/${shopId}/`, patch);
  return data;
};
