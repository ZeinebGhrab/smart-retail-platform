import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { IonContent, IonPage } from '@ionic/react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

import {
  getSummary,
  getVisitorHistory,
  getForecast,
  SummaryResponse,
  DailyHistoryRow,
  ForecastResponse,
} from '../services/api';
import './Historique.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const CAMERA_FILTERS = [
  { value: 'toutes',     label: 'Toutes' },
  { value: 'Porte_nord', label: 'Porte Nord' },
  { value: 'Porte_sud',  label: 'Porte Sud' },
];

const PAGE_SIZE = 10;

function formatDateShort(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
}

// Réponse paginée de l'API visitor_history
interface HistoryPage {
  count: number;
  limit: number;
  offset: number;
  results: DailyHistoryRow[];
}

const Historique: React.FC = () => {
  const [camera, setCamera]     = useState<string>('toutes');
  const [summary, setSummary]   = useState<SummaryResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);

  // Graphique : 14 jours fixes (offset 0)
  const [chartRows, setChartRows] = useState<DailyHistoryRow[]>([]);

  // Tableau paginé
  const [histPage, setHistPage]   = useState<HistoryPage | null>(null);
  const [tableOffset, setTableOffset] = useState(0);

  const [loading, setLoading]       = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [error, setError]           = useState<string | null>(null);

  // ── Chargement initial (summary + forecast + graphique + page 1 tableau) ──
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTableOffset(0);

    const cameraParam = camera === 'toutes' ? undefined : camera;

    Promise.all([
      getSummary(),
      getForecast({ camera: cameraParam }),
      // Graphique : 14 derniers jours
      getVisitorHistory({ camera: cameraParam, limit: '14', offset: '0' } as any),
      // Tableau : première page
      getVisitorHistory({ camera: cameraParam, limit: String(PAGE_SIZE), offset: '0' } as any),
    ])
      .then(([summaryRes, forecastRes, chartRes, tableRes]) => {
        if (cancelled) return;
        setSummary(summaryRes);
        setForecast(forecastRes);
        // Le graphique utilise les résultats du plus ancien au plus récent
        setChartRows((chartRes as any).results ?? []);
        setHistPage(tableRes as unknown as HistoryPage);
      })
      .catch((err) => { if (!cancelled) setError(err.message || 'Erreur de chargement'); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [camera]);

  // ── Changement de page du tableau ─────────────────────────────
  const loadTablePage = useCallback((newOffset: number) => {
    setTableLoading(true);
    const cameraParam = camera === 'toutes' ? undefined : camera;
    getVisitorHistory({ camera: cameraParam, limit: String(PAGE_SIZE), offset: String(newOffset) } as any)
      .then((res) => {
        setHistPage(res as unknown as HistoryPage);
        setTableOffset(newOffset);
      })
      .finally(() => setTableLoading(false));
  }, [camera]);

  // ── Données tableau ────────────────────────────────────────────
  const tableRows   = histPage?.results ?? [];
  const totalCount  = histPage?.count   ?? 0;
  const totalPages  = Math.ceil(totalCount / PAGE_SIZE);
  const currentPage = Math.floor(tableOffset / PAGE_SIZE) + 1;

  const pageNumbers = useMemo(() => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const start = Math.max(1, currentPage - 2);
    const end   = Math.min(totalPages, start + 4);
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }, [totalPages, currentPage]);

  // ── Graphique ──────────────────────────────────────────────────
  const chartData = useMemo(() => ({
    labels: chartRows.map((r) => formatDateShort(r.date)),
    datasets: [{
      label: 'Visiteurs',
      data: chartRows.map((r) => r.visit_Count),
      backgroundColor: 'rgba(37, 99, 235, 0.55)',
      hoverBackgroundColor: '#2563eb',
      borderRadius: 4,
      maxBarThickness: 22,
    }],
  }), [chartRows]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#6b7280', font: { size: 9 }, maxRotation: 0 } },
      y: { grid: { color: 'rgba(15,23,42,0.07)' }, ticks: { color: '#6b7280', font: { size: 9 }, maxTicksLimit: 5 } },
    },
  } as const;

  return (
    <IonPage className="hist-page">

      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="hist-header">
        <div className="hist-header-top">
          <div>
            <div className="hist-title">Historique &amp; prévisions</div>
            <div className="hist-subtitle">Analyse de fréquentation par caméra</div>
          </div>
        </div>
        <div className="hist-filter-row">
          {CAMERA_FILTERS.map((f) => (
            <button
              key={f.value}
              className={`hist-filter-pill ${camera === f.value ? 'active' : ''}`}
              onClick={() => setCamera(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ─────────────────────────────────────────────── */}
      <IonContent className="hist-content">

        {loading && (
          <div className="hist-loading">
            <div className="hist-spinner" />
            <p>Chargement des données…</p>
          </div>
        )}

        {error && !loading && (
          <div className="hist-error-card">
            <span className="ti ti-alert-triangle hist-error-icon" aria-hidden="true" />
            <div>
              <div className="hist-error-title">Connexion à l'API impossible</div>
              <div className="hist-error-msg">
                Impossible de contacter le backend Django ({error}). Vérifiez qu'il
                tourne sur <code>localhost:8000</code>.
              </div>
            </div>
          </div>
        )}

        {!loading && !error && summary && (
          <>
            {/* KPIs */}
            <div className="hist-kpi-grid">
              <div className="hist-kpi-card">
                <div className="hist-kpi-label">
                  <span className="ti ti-users" aria-hidden="true" /> Total visiteurs
                </div>
                <div className="hist-kpi-value">{summary.total_visits.toLocaleString('fr-FR')}</div>
                <div className="hist-kpi-sub">{summary.period.start_date} → {summary.period.end_date}</div>
              </div>

              <div className="hist-kpi-card">
                <div className="hist-kpi-label">
                  <span className="ti ti-gender-bigender" aria-hidden="true" /> Hommes / Femmes
                </div>
                <div className="hist-kpi-value">
                  {summary.by_gender.men.toLocaleString('fr-FR')} / {summary.by_gender.women.toLocaleString('fr-FR')}
                </div>
                <div className="hist-kpi-sub">Répartition cumulée</div>
              </div>

              <div className="hist-kpi-card">
                <div className="hist-kpi-label">
                  <span className="ti ti-calendar-stats" aria-hidden="true" /> Jours d'historique
                </div>
                <div className="hist-kpi-value">{summary.period.n_days}</div>
                <div className="hist-kpi-sub">Période analysée</div>
              </div>

              <div className="hist-kpi-card hist-kpi-forecast">
                <div className="hist-kpi-label">
                  <span className="ti ti-sparkles" aria-hidden="true" /> Prévision {forecast?.target_date}
                </div>
                <div className="hist-kpi-value">
                  {forecast?.predicted_visit_count.toLocaleString('fr-FR') ?? '—'}
                </div>
                <div className="hist-kpi-sub">Confiance : {forecast?.confidence ?? '—'}</div>
              </div>
            </div>

            {/* Graphique */}
            <div className="hist-chart-card">
              <div className="hist-chart-header">
                <span className="hist-chart-title">Tendance — 14 derniers jours</span>
                <span className="hist-chart-badge">{chartRows.length} jours</span>
              </div>
              <div className="hist-chart-wrap">
                <Bar data={chartData} options={chartOptions} />
              </div>
            </div>

            {/* ── Tableau paginé ───────────────────────────────── */}
            <div className="hist-section-header">
              <span className="hist-section-title">Détail journalier</span>
              {totalCount > 0 && (
                <span className="hist-section-count">{totalCount} jours au total</span>
              )}
            </div>

            <div className={`hist-row-list ${tableLoading ? 'hist-table-loading' : ''}`}>
              {tableRows.map((row) => (
                <div key={`${row.date}-${row.camera}`} className="hist-row-card">
                  <div className="hist-row-main">
                    <div className="hist-row-date">{formatDateShort(row.date)}</div>
                    <div className="hist-row-camera">{row.camera}</div>
                  </div>
                  <div className="hist-row-count">
                    <span className="ti ti-users" aria-hidden="true" />
                    {row.visit_Count.toLocaleString('fr-FR')}
                  </div>
                  <div className="hist-row-breakdown">
                    <span className="hist-chip">H {row.gender_men}</span>
                    <span className="hist-chip">F {row.gender_women}</span>
                    <span className="hist-chip hist-chip-muted">Enf. {row.age_child}</span>
                    <span className="hist-chip hist-chip-muted">Ado {row.age_teenager}</span>
                    <span className="hist-chip hist-chip-muted">Adu. {row.age_adult}</span>
                    <span className="hist-chip hist-chip-muted">Sén. {row.age_senior}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* ── Contrôles de pagination ──────────────────────── */}
            {totalPages > 1 && (
              <div className="hist-pagination">
                <button
                  className="hist-page-btn"
                  disabled={currentPage === 1 || tableLoading}
                  onClick={() => loadTablePage((currentPage - 2) * PAGE_SIZE)}
                  aria-label="Page précédente"
                >
                  ‹
                </button>

                {pageNumbers[0] > 1 && (
                  <>
                    <button className="hist-page-btn" onClick={() => loadTablePage(0)}>1</button>
                    {pageNumbers[0] > 2 && <span className="hist-page-ellipsis">…</span>}
                  </>
                )}

                {pageNumbers.map((p) => (
                  <button
                    key={p}
                    className={`hist-page-btn ${p === currentPage ? 'active' : ''}`}
                    disabled={tableLoading}
                    onClick={() => loadTablePage((p - 1) * PAGE_SIZE)}
                  >
                    {p}
                  </button>
                ))}

                {pageNumbers[pageNumbers.length - 1] < totalPages && (
                  <>
                    {pageNumbers[pageNumbers.length - 1] < totalPages - 1 && (
                      <span className="hist-page-ellipsis">…</span>
                    )}
                    <button
                      className="hist-page-btn"
                      onClick={() => loadTablePage((totalPages - 1) * PAGE_SIZE)}
                    >
                      {totalPages}
                    </button>
                  </>
                )}

                <button
                  className="hist-page-btn"
                  disabled={currentPage === totalPages || tableLoading}
                  onClick={() => loadTablePage(currentPage * PAGE_SIZE)}
                  aria-label="Page suivante"
                >
                  ›
                </button>

                <span className="hist-page-info">
                  Page {currentPage}/{totalPages}
                </span>
              </div>
            )}

            <div style={{ height: 16 }} />
          </>
        )}

      </IonContent>
    </IonPage>
  );
};

export default Historique;