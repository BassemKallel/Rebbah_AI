import axios from 'axios';

const BASE_URL =
  (process.env.REACT_APP_CRM_API_URL || 'http://localhost:8000/api/v1/crm')
    .replace('/crm', '/auth');

const authClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

export interface LoginResponse {
  access: string;
  refresh: string;
  user: { id: number; username: string; email: string };
  shop_id: string;
  company_name: string;
  response_mode: string;
}

export interface MeResponse {
  user: { id: number; username: string; email: string };
  company: {
    shop_id: string;
    name: string;
    response_mode: string;
    has_gemini_key: boolean;
    has_llm_context: boolean;
    is_active: boolean;
  };
  role: string;
}

export const loginApi = (username: string, password: string) =>
  authClient.post<LoginResponse>('/login/', { username, password });

export const refreshApi = (refresh: string) =>
  authClient.post<{ access: string }>('/refresh/', { refresh });

export const meApi = (token: string) =>
  authClient.get<MeResponse>('/me/', {
    headers: { Authorization: `Bearer ${token}` },
  });
