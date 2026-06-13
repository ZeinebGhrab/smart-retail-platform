// ============================================================
// src/services/api.ts — Client API pour le backend Django
// (historique visiteurs / analytics)
// ============================================================

// URL de base de l'API Django. Configurable via la variable
// d'environnement Vite VITE_API_URL (voir .env / .env.example).
export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api';

async function getJSON<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, value);
      }
    });
  }

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Erreur API (${res.status}) sur ${url.pathname}`);
  }
  return res.json() as Promise<T>;
}

// ------------------------------------------------------------
// Types
// ------------------------------------------------------------
export interface DailyHistoryRow {
  date: string;
  camera: string;
  visit_Count: number;
  gender_men: number;
  gender_women: number;
  age_child: number;
  age_teenager: number;
  age_adult: number;
  age_senior: number;
}

export interface VisitorHistoryResponse {
  start_date: string | null;
  end_date: string | null;
  camera: string;
  count: number;
  results: DailyHistoryRow[];
}

export interface VisitorCountResponse {
  date: string;
  camera: string;
  visit_count: number | null;
  breakdown?: DailyHistoryRow[];
  message?: string;
}

export interface HourlyFlowPoint {
  hour: number;
  count: number;
}

export interface HourlyFlowResponse {
  date: string;
  camera: string;
  hourly_flow: HourlyFlowPoint[];
  total?: number;
  peak_hour?: number;
  message?: string;
}

export interface ForecastResponse {
  target_date: string;
  camera: string;
  predicted_visit_count: number;
  method: string;
  confidence: string;
  model_status: string;
  n_historical_points?: number;
  message: string;
}

export interface SummaryResponse {
  period: { start_date: string; end_date: string; n_days: number };
  total_visits: number;
  by_camera: { camera: string; visit_Count: number }[];
  by_gender: { men: number; women: number };
  by_age: { child: number; teenager: number; adult: number; senior: number };
  cameras: string[];
}

export interface CamerasResponse {
  cameras: string[];
}

// ------------------------------------------------------------
// Endpoints
// ------------------------------------------------------------

/** Historique journalier des visiteurs (analytics). */
export function getVisitorHistory(params?: {
  start_date?: string;
  end_date?: string;
  camera?: string;
}): Promise<VisitorHistoryResponse> {
  return getJSON<VisitorHistoryResponse>('/history/visitors/', params);
}

/** Nombre de visiteurs pour une date donnée (par défaut : dernière date dispo). */
export function getVisitorCount(params?: {
  date?: string;
  camera?: string;
}): Promise<VisitorCountResponse> {
  return getJSON<VisitorCountResponse>('/history/visitors/count/', params);
}

/** Flux horaire de visiteurs pour une date donnée. */
export function getHourlyFlow(params?: {
  date?: string;
  camera?: string;
}): Promise<HourlyFlowResponse> {
  return getJSON<HourlyFlowResponse>('/history/visitors/hourly/', params);
}

/** Prévision du nombre de visiteurs (régression linéaire). */
export function getForecast(params?: {
  date?: string;
  camera?: string;
}): Promise<ForecastResponse> {
  return getJSON<ForecastResponse>('/history/visitors/forecast/', params);
}

/** KPIs globaux : période, totaux, répartition par caméra/genre/âge. */
export function getSummary(): Promise<SummaryResponse> {
  return getJSON<SummaryResponse>('/history/summary/');
}

/** Liste des caméras disponibles. */
export function getCameras(): Promise<CamerasResponse> {
  return getJSON<CamerasResponse>('/history/cameras/');
}