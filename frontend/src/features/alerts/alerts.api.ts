// ============================================================
// src/features/alerts/alerts.api.ts
//
// Les cookies HttpOnly (anavid_access) sont envoyés automatiquement
// par le navigateur grâce à credentials: 'include'.
// authAxios est utilisé pour bénéficier du refresh automatique sur 401.
// ============================================================

import authAxios from '../../services/authAxios';
import { SecurityAlert, AlertStatus } from './alert.model';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// ── Mapping BD → AlertStatus frontend ──────────────────────────
function mapStatus(qualification: string | null): AlertStatus {
  if (!qualification) return 'en_attente';
  const map: Record<string, AlertStatus> = {
    vol:         'vol_confirme_interpelle',
    suspicious:  'comportement_suspect',
    false_alarm: 'fausse_alerte',
  };
  return map[qualification] ?? 'en_attente';
}

// ── Mapper la réponse API → SecurityAlert ──────────────────────
function mapVideo(v: any): SecurityAlert {
  return {
    id:           String(v.id),
    cameraId:     v.code ?? '',
    cameraLabel:  v.code ?? '',
    location:     v.space_name ?? '',
    rawTag:       v.code,
    message:      v.comment ?? '',
    confidence:   v.probability != null ? Math.round(v.probability * 100) : 0,
    videoUrl:     v.path,
    createdAt:    v.recording_date,
    status:       mapStatus(v.qualification),
    qualifiedBy:  v.assigned_to ?? undefined,
  };
}

// ── Réponse paginée ────────────────────────────────────────────
export interface AlertsPage {
  count: number;
  limit: number;
  offset: number;
  results: SecurityAlert[];
}

// ── Fetch alertes (paginées) ───────────────────────────────────
// Mapping filtre frontend → qualification backend
export const FILTER_TO_QUALIFICATION: Record<string, string | null | undefined> = {
  tous:                      undefined,   // pas de filtre
  en_attente:                'null',      // qualification IS NULL
  vol_confirme_interpelle:   'vol',
  comportement_suspect:      'suspicious',
  fausse_alerte:             'false_alarm',
};

export async function fetchAlerts(
  options: {
    spaceId?: number;
    orgId?: number;
    limit?: number;
    offset?: number;
    qualification?: string | null;
  } = {}
): Promise<AlertsPage> {
  const { spaceId, orgId, limit = 10, offset = 0, qualification } = options;

  let path = '';
  if (spaceId)     path = `/videos/space/${spaceId}/`;
  else if (orgId)  path = `/videos/organisation/${orgId}/`;
  else             path = `/videos/all/`;

  const params: Record<string, string> = {
    limit:  String(limit),
    offset: String(offset),
  };
  if (qualification !== undefined && qualification !== null) {
    params.qualification = qualification;
  }

  // CORRECTIF : authAxios envoie les cookies HttpOnly automatiquement
  // (withCredentials: true) et gère le refresh sur 401.
  // Plus besoin de header Authorization manuel.
  const res = await authAxios.get<any>(path, { params });
  const data = res.data;

  const items: SecurityAlert[] = (Array.isArray(data) ? data : (data.results ?? [])).map(mapVideo);
  return {
    count:   data.count  ?? items.length,
    limit:   data.limit  ?? limit,
    offset:  data.offset ?? offset,
    results: items,
  };
}

// ── Fetch une alerte par id ────────────────────────────────────
export async function fetchAlertById(id: string): Promise<SecurityAlert> {
  try {
    const res = await authAxios.get<any>(`/videos/${id}/`);
    return mapVideo(res.data);
  } catch {
    // Fallback : cherche dans la liste complète
    const page = await fetchAlerts();
    const found = page.results.find(a => a.id === id);
    if (!found) throw new Error('Alerte introuvable');
    return found;
  }
}

// ── Qualifier une alerte ───────────────────────────────────────
type QualifyPayload = {
  status: string;
  qualification?: string;
  approval_result?: string;
};

export async function qualifyAlert(id: string, status: AlertStatus): Promise<SecurityAlert> {
  const payloadMap: Record<AlertStatus, QualifyPayload> = {
    vol_confirme_interpelle:     { status: 'APPROVED', qualification: 'vol',         approval_result: 'TP' },
    vol_confirme_non_interpelle: { status: 'APPROVED', qualification: 'vol',         approval_result: 'TP' },
    comportement_suspect:        { status: 'APPROVED', qualification: 'suspicious',  approval_result: 'TP' },
    fausse_alerte:               { status: 'APPROVED', qualification: 'false_alarm', approval_result: 'TN' },
    en_attente:                  { status: 'PENDING' },
  };

  const payload = payloadMap[status] ?? { status: 'PENDING' };

  const res = await authAxios.patch<any>(`/videos/${id}/qualify/`, payload);
  const data = res.data;
  return mapVideo(data.alert ?? data);
}

// ── Fetch les espaces disponibles ──────────────────────────────
export async function fetchSpaces() {
  const res = await authAxios.get<any>('/videos/spaces/');
  return res.data;
}