import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { loginApi, refreshApi, LoginResponse } from '../api/authApi';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  shopId: string | null;
  companyName: string | null;
  username: string | null;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const STORAGE_KEYS = {
  access: 'tiktak_access_token',
  refresh: 'tiktak_refresh_token',
  shopId: 'tiktak_shop_id',
  companyName: 'tiktak_company_name',
  username: 'tiktak_username',
} as const;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    accessToken: null,
    refreshToken: null,
    shopId: null,
    companyName: null,
    username: null,
  });

  // ── Restore session from localStorage ──────────────────────────────
  useEffect(() => {
    const access = localStorage.getItem(STORAGE_KEYS.access);
    const refresh = localStorage.getItem(STORAGE_KEYS.refresh);
    const shopId = localStorage.getItem(STORAGE_KEYS.shopId);
    const companyName = localStorage.getItem(STORAGE_KEYS.companyName);
    const username = localStorage.getItem(STORAGE_KEYS.username);

    if (access && refresh) {
      setState({
        isAuthenticated: true,
        isLoading: false,
        accessToken: access,
        refreshToken: refresh,
        shopId,
        companyName,
        username,
      });
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  // ── Login ───────────────────────────────────────────────────────────
  const login = useCallback(async (username: string, password: string) => {
    const { data } = await loginApi(username, password);
    persistSession(data);
    setState({
      isAuthenticated: true,
      isLoading: false,
      accessToken: data.access,
      refreshToken: data.refresh,
      shopId: data.shop_id,
      companyName: data.company_name,
      username: data.user.username,
    });
  }, []);

  // ── Logout ──────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    clearSession();
    setState({
      isAuthenticated: false,
      isLoading: false,
      accessToken: null,
      refreshToken: null,
      shopId: null,
      companyName: null,
      username: null,
    });
  }, []);

  // ── Auto-refresh token ──────────────────────────────────────────────
  useEffect(() => {
    if (!state.refreshToken) return;

    // Refresh 5 minutes before expiry (access token = 1h)
    const interval = setInterval(async () => {
      try {
        const { data } = await refreshApi(state.refreshToken!);
        localStorage.setItem(STORAGE_KEYS.access, data.access);
        setState((s) => ({ ...s, accessToken: data.access }));
      } catch {
        // Refresh failed — force logout
        clearSession();
        setState((s) => ({
          ...s,
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
        }));
      }
    }, 50 * 60 * 1000); // Every 50 minutes

    return () => clearInterval(interval);
  }, [state.refreshToken]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function persistSession(data: LoginResponse) {
  localStorage.setItem(STORAGE_KEYS.access, data.access);
  localStorage.setItem(STORAGE_KEYS.refresh, data.refresh);
  localStorage.setItem(STORAGE_KEYS.shopId, data.shop_id);
  localStorage.setItem(STORAGE_KEYS.companyName, data.company_name);
  localStorage.setItem(STORAGE_KEYS.username, data.user.username);
}

function clearSession() {
  Object.values(STORAGE_KEYS).forEach((k) => localStorage.removeItem(k));
}

/**
 * Returns the current access token from localStorage.
 * Used by Axios interceptors outside of React context.
 */
export function getAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.access);
}

export function getShopId(): string | null {
  return localStorage.getItem(STORAGE_KEYS.shopId);
}
