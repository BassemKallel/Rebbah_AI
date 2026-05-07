import axios from 'axios';

const BASE_URL =
  (process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000') + '/api/v1/auth';

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
  dashboard_token: string;
  role?: string;
}

export interface MeResponse {
  user: { id: number; username: string; email: string } | null;
  company: {
    shop_id: string;
    name: string;
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
