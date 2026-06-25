import { getAccessToken } from './auth';
import { SecurityAlert, AlertStatus } from './alert';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const headers = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${getAccessToken()}`,
});

// Mapper la réponse API → SecurityAlert (interface existante)
function mapVideo(v: any): SecurityAlert {
  return {
    id: String(v.id),
    cameraId: v.code ?? '',
    cameraLabel: v.code ?? '',
    location: v.space_name ?? '',
    rawTag: v.code,
    message: v.msg,
    confidence: v.probability != null ? Math.round(v.probability * 100) : 0,
    videoUrl: v.path,
    createdAt: v.recording_date,
    status: mapStatus(v.qualification),
    qualifiedBy: v.qualification ?? undefined,
  };
}

function mapStatus(qualification: string | null): AlertStatus {
  if (!qualification) return 'en_attente';
  const map: Record<string, AlertStatus> = {
    VA: 'vol_confirme_interpelle',
    VS: 'comportement_suspect',
    FA: 'fausse_alerte',
    PE: 'en_attente',
  };
  return map[qualification] ?? 'en_attente';
}

export async function fetchAlerts(spaceId?: number, orgId?: number): Promise<SecurityAlert[]> {
  let url = '';
  if (spaceId) url = `${API}/videos/space/${spaceId}/`;
  else if (orgId) url = `${API}/videos/organisation/${orgId}/`;
  else url = `${API}/videos/all/`;// défaut

  const res = await fetch(url, { headers: headers() });
  if (!res.ok) throw new Error('Erreur chargement alertes');
  const data = await res.json();
  return data.map(mapVideo);
}

export async function fetchAlertById(id: string): Promise<SecurityAlert> {
  // On recharge la liste et on filtre par id (pas d'endpoint detail séparé)
  const all = await fetchAlerts();
  const found = all.find(a => a.id === id);
  if (!found) throw new Error('Alerte introuvable');
  return found;
}

export async function qualifyAlert(id: string, status: AlertStatus): Promise<SecurityAlert> {
  const reverseMap: Record<AlertStatus, string> = {
    vol_confirme_interpelle: 'VA',
    vol_confirme_non_interpelle: 'VA',
    comportement_suspect: 'VS',
    fausse_alerte: 'FA',
    en_attente: 'PE',
  };

  const res = await fetch(`${API}/videos/${id}/qualify/`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify({ status: reverseMap[status], qualification: status }),
  });
  if (!res.ok) throw new Error('Erreur qualification');
  return mapVideo(await res.json());
}

export async function fetchSpaces() {
  const res = await fetch(`${API}/videos/spaces/`, { headers: headers() });
  if (!res.ok) throw new Error('Erreur chargement spaces');
  return res.json();
}