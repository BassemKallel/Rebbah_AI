/**
 * axiosInstance.ts — Shared Axios instance with JWT interceptor.
 *
 * All API services import this instance instead of creating their own.
 * Handles:
 * - Automatic JWT injection from localStorage
 * - Redirect to /login on 401 responses
 */
import axios from 'axios';
import { getAccessToken } from '../providers/AuthProvider';

const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const defaultUrl = isLocal ? 'http://localhost:8010' : window.location.origin;
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || defaultUrl;

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Inject JWT on every request
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
