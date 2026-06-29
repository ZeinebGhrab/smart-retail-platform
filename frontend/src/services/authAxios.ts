// ============================================================
// src/services/authAxios.ts
// Instance Axios sécurisée (stratégie COOKIE HttpOnly) :
//   • withCredentials: true → les cookies HttpOnly voyagent automatiquement
//   • Plus d'injection manuelle du Bearer token
//   • Sur 401 → POST /api/auth/refresh/ (le backend lit le cookie refresh
//     et pose un nouveau cookie access)
//   • Si le refresh échoue → clearSession() + événement "auth:expired"
// ============================================================

import axios, {
  AxiosInstance,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';
import { clearSession } from './auth';
import { API_BASE_URL } from './api';

// ── Instance principale ─────────────────────────────────────
const authAxios: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,                          // <-- clé de voûte
  headers: { 'Content-Type': 'application/json' },
});

// Pas de request interceptor pour injecter un token :
// le cookie HttpOnly est envoyé automatiquement par le navigateur.

// ── File d'attente pour les requêtes simultanées ────────────
let isRefreshing = false;
let refreshQueue: Array<{
  resolve: () => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown = null): void {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  refreshQueue = [];
}

// ── Response interceptor : gère les 401 ────────────────────
authAxios.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    const is401 = error.response?.status === 401;
    const alreadyRetried = originalRequest._retry;
    const isAuthEndpoint =
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/register') ||
      originalRequest.url?.includes('/auth/refresh');

    if (!is401 || alreadyRetried || isAuthEndpoint) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<void>((resolve, reject) => {
        refreshQueue.push({ resolve, reject });
      })
        .then(() => authAxios(originalRequest))
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Le backend lit "anavid_refresh" et pose un nouveau "anavid_access"
      await axios.post(`${API_BASE_URL}/auth/refresh/`, {}, { withCredentials: true });
      processQueue();
      return authAxios(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError);
      clearSession();
      redirectToLogin();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

// ── Redirect helper ─────────────────────────────────────────
function redirectToLogin(): void {
  if (window.location.pathname === '/login') return;
  window.dispatchEvent(new Event('auth:expired'));
  setTimeout(() => {
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }, 300);
}

export default authAxios;