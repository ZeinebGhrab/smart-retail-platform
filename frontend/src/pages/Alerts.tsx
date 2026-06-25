import React, { useEffect, useMemo, useState } from 'react';
import { IonPage, IonContent, useIonRouter } from '@ionic/react';
import { SecurityAlert, AlertStatus, ALERT_STATUS_LABELS } from '../services/alert';
import { fetchAlerts } from '../services/alerts';
import './Alerts.css';

type FilterKey = 'tous' | AlertStatus;

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'tous', label: 'Tous' },
  { key: 'en_attente', label: 'En attente' },
  { key: 'vol_confirme_interpelle', label: 'Vol confirmé' },
  { key: 'comportement_suspect', label: 'Suspect' },
  { key: 'fausse_alerte', label: 'Fausse alerte' },
];

const STATUS_BADGE_CLASS: Record<AlertStatus, string> = {
  en_attente: 'badge-pending',
  vol_confirme_interpelle: 'badge-confirmed',
  vol_confirme_non_interpelle: 'badge-confirmed',
  comportement_suspect: 'badge-suspect',
  fausse_alerte: 'badge-false',
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "à l'instant";
  if (min < 60) return `il y a ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `il y a ${h}h`;
  const d = Math.floor(h / 24);
  return `il y a ${d}j`;
}

const Alerts: React.FC = () => {
  const ionRouter = useIonRouter();
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [filter, setFilter] = useState<FilterKey>('tous');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchAlerts()
      .then((data) => mounted && setAlerts(data))
      .catch(() => mounted && setError('Impossible de charger les alertes.'))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (filter === 'tous') return alerts;
    return alerts.filter((a) => a.status === filter);
  }, [alerts, filter]);

  const openDetail = (id: string) => ionRouter.push(`/alerts/${id}`);

  return (
    <IonPage>
      <IonContent fullscreen className="alerts-content">
        <div className="alerts-header">
          <h1>
            Alertes sécurité <span className="alerts-count">({alerts.length})</span>
          </h1>
        </div>

        <div className="alerts-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`alert-filter-chip ${filter === f.key ? 'active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading && <div className="alerts-state">Chargement…</div>}
        {!loading && error && <div className="alerts-state error">{error}</div>}
        {!loading && !error && filtered.length === 0 && (
          <div className="alerts-state">Aucune alerte pour ce filtre.</div>
        )}

        <div className="alerts-list">
          {filtered.map((a) => (
            <button key={a.id} className="alert-card" onClick={() => openDetail(a.id)}>
              <div className="alert-thumb">
                {a.thumbnailUrl ? <img src={a.thumbnailUrl} alt="" /> : <span className="ti ti-player-play-filled" />}
                <span className="alert-confidence">{a.confidence}%</span>
              </div>

              <div className="alert-info">
                <div className="alert-camera-row">
                  {a.status === 'en_attente' && <span className="alert-dot" />}
                  <h3>{a.cameraLabel}</h3>
                </div>
                <p className="alert-location">{a.location}</p>
                <p className="alert-time">{timeAgo(a.createdAt)}</p>
              </div>

              <span className={`alert-badge ${STATUS_BADGE_CLASS[a.status]}`}>
                {ALERT_STATUS_LABELS[a.status]}
              </span>
            </button>
          ))}
        </div>
      </IonContent>
    </IonPage>
  );
};

export default Alerts;
