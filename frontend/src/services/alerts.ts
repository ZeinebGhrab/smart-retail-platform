import { getAccessToken } from './auth';
import { SecurityAlert, AlertStatus } from './alert';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const headers = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${getAccessToken()}`,
});

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
    qualification?: string | null;  // valeur backend : 'vol' | 'suspicious' | 'false_alarm' | 'null' | undefined
  } = {}
): Promise<AlertsPage> {
  const { spaceId, orgId, limit = 10, offset = 0, qualification } = options;

  let url = '';
  if (spaceId)     url = `${API}/videos/space/${spaceId}/`;
  else if (orgId)  url = `${API}/videos/organisation/${orgId}/`;
  else             url = `${API}/videos/all/`;

  const params = new URLSearchParams({
    limit:  String(limit),
    offset: String(offset),
  });
  // Filtre par qualification (envoyé seulement si défini)
  if (qualification !== undefined && qualification !== null) {
    params.set('qualification', qualification);
  }

  const res = await fetch(`${url}?${params}`, { headers: headers() });
  if (!res.ok) throw new Error('Erreur chargement alertes');
  const data = await res.json();

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
  const res = await fetch(`${API}/videos/${id}/`, { headers: headers() });
  if (!res.ok) {
    const page = await fetchAlerts();
    const found = page.results.find(a => a.id === id);
    if (!found) throw new Error('Alerte introuvable');
    return found;
  }
  return mapVideo(await res.json());
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
    fausse_alerte:               { status: 'REJECTED', qualification: 'false_alarm', approval_result: 'TN' },
    en_attente:                  { status: 'PENDING' },
  };

  const payload = payloadMap[status] ?? { status: 'PENDING' };

  const res = await fetch(`${API}/videos/${id}/qualify/`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Erreur qualification');
  const data = await res.json();
  return mapVideo(data.alert ?? data);
}

// ── Fetch les espaces disponibles ──────────────────────────────
export async function fetchSpaces() {
  const res = await fetch(`${API}/videos/spaces/`, { headers: headers() });
  if (!res.ok) throw new Error('Erreur chargement spaces');
  return res.json();
}