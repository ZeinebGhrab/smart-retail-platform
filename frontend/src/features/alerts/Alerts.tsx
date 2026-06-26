import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { IonPage, IonContent, useIonRouter } from '@ionic/react';
import { SecurityAlert, AlertStatus, ALERT_STATUS_LABELS } from './alert.model';
import { fetchAlerts, AlertsPage, FILTER_TO_QUALIFICATION } from './alerts.api';
import './Alerts.css';

type FilterKey = 'tous' | AlertStatus;

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'tous',                      label: 'Tous' },
  { key: 'en_attente',                label: 'En attente' },
  { key: 'vol_confirme_interpelle',   label: 'Vol confirmé' },
  { key: 'comportement_suspect',      label: 'Suspect' },
  { key: 'fausse_alerte',             label: 'Fausse alerte' },
];

const STATUS_BADGE_CLASS: Record<AlertStatus, string> = {
  en_attente:                  'badge-pending',
  vol_confirme_interpelle:     'badge-confirmed',
  vol_confirme_non_interpelle: 'badge-confirmed',
  comportement_suspect:        'badge-suspect',
  fausse_alerte:               'badge-false',
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

const PAGE_SIZE = 10;

const Alerts: React.FC = () => {
  const ionRouter = useIonRouter();
  const [page, setPage]       = useState<AlertsPage | null>(null);
  const [offset, setOffset]   = useState(0);
  const [filter, setFilter]   = useState<FilterKey>('tous');
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  // ── Chargement paginé avec filtre backend ──────────────────────
  const load = useCallback((newOffset: number, activeFilter: FilterKey) => {
    setLoading(true);
    setError(null);
    const qualification = FILTER_TO_QUALIFICATION[activeFilter];
    fetchAlerts({ limit: PAGE_SIZE, offset: newOffset, qualification })
      .then((data) => { setPage(data); setOffset(newOffset); })
      .catch(() => setError('Impossible de charger les alertes.'))
      .finally(() => setLoading(false));
  }, []);

  // Rechargement quand le filtre change → reset page 1
  useEffect(() => { load(0, filter); }, [filter, load]);

  const alerts      = page?.results ?? [];
  const total       = page?.count   ?? 0;
  const totalPages  = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const openDetail = (id: string) => ionRouter.push(`/alerts/${id}`);

  const goTo = (pageNum: number) => load((pageNum - 1) * PAGE_SIZE, filter);

  const handleFilter = (key: FilterKey) => {
    setFilter(key);
    setOffset(0);
    // useEffect réagit au changement de filter
  };

  // Fenêtre glissante de pages
  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const start = Math.max(1, currentPage - 2);
    const end   = Math.min(totalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [totalPages, currentPage]);

  return (
    <IonPage>
      <IonContent fullscreen className="alerts-content">
        <div className="alerts-header">
          <h1>
            Alertes sécurité{' '}
            <span className="alerts-count">
              ({total} {filter !== 'tous' ? `résultat${total > 1 ? 's' : ''}` : 'au total'})
            </span>
          </h1>
        </div>

        <div className="alerts-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`alert-filter-chip ${filter === f.key ? 'active' : ''}`}
              onClick={() => handleFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {loading && <div className="alerts-state">Chargement…</div>}
        {!loading && error && <div className="alerts-state error">{error}</div>}
        {!loading && !error && alerts.length === 0 && (
          <div className="alerts-state">Aucune alerte pour ce filtre.</div>
        )}

        {!loading && !error && (
          <div className="alerts-list">
            {alerts.map((a) => (
              <button key={a.id} className="alert-card" onClick={() => openDetail(a.id)}>
                <div className="alert-thumb">
                  {a.thumbnailUrl
                    ? <img src={a.thumbnailUrl} alt="" />
                    : <span className="ti ti-player-play-filled" />}
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
        )}

        {/* ── Pagination ───────────────────────────────────────── */}
        {!loading && !error && totalPages > 1 && (
          <div className="alerts-pagination">
            <button
              className="alerts-page-btn"
              disabled={currentPage === 1}
              onClick={() => goTo(currentPage - 1)}
              aria-label="Page précédente"
            >
              ‹
            </button>

            {pageNumbers[0] > 1 && (
              <>
                <button className="alerts-page-btn" onClick={() => goTo(1)}>1</button>
                {pageNumbers[0] > 2 && <span className="alerts-page-ellipsis">…</span>}
              </>
            )}

            {pageNumbers.map((p) => (
              <button
                key={p}
                className={`alerts-page-btn ${p === currentPage ? 'active' : ''}`}
                onClick={() => goTo(p)}
              >
                {p}
              </button>
            ))}

            {pageNumbers[pageNumbers.length - 1] < totalPages && (
              <>
                {pageNumbers[pageNumbers.length - 1] < totalPages - 1 && (
                  <span className="alerts-page-ellipsis">…</span>
                )}
                <button className="alerts-page-btn" onClick={() => goTo(totalPages)}>
                  {totalPages}
                </button>
              </>
            )}

            <button
              className="alerts-page-btn"
              disabled={currentPage === totalPages}
              onClick={() => goTo(currentPage + 1)}
              aria-label="Page suivante"
            >
              ›
            </button>

            <span className="alerts-page-info">
              Page {currentPage}/{totalPages}
            </span>
          </div>
        )}

      </IonContent>
    </IonPage>
  );
};

export default Alerts;