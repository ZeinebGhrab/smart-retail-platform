import React, { useEffect, useMemo, useState } from 'react';
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

function formatDateShort(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
}

const Historique: React.FC = () => {
  const [camera, setCamera] = useState<string>('toutes');
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [rows, setRows] = useState<DailyHistoryRow[]>([]);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const cameraParam = camera === 'toutes' ? undefined : camera;

    Promise.all([
      getSummary(),
      getVisitorHistory({ camera: cameraParam }),
      getForecast({ camera: cameraParam }),
    ])
      .then(([summaryRes, historyRes, forecastRes]) => {
        if (cancelled) return;
        setSummary(summaryRes);
        // Affiche les 14 derniers jours, du plus ancien au plus récent (pour le graphe)
        setRows(historyRes.results.slice(-14));
        setForecast(forecastRes);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Erreur de chargement');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [camera]);

  const tableRows = useMemo(() => [...rows].reverse(), [rows]);

  const chartData = useMemo(() => ({
    labels: rows.map((r) => formatDateShort(r.date)),
    datasets: [
      {
        label: 'Visiteurs',
        data: rows.map((r) => r.visit_Count),
        backgroundColor: 'rgba(37, 99, 235, 0.55)',
        hoverBackgroundColor: '#2563eb',
        borderRadius: 4,
        maxBarThickness: 22,
      },
    ],
  }), [rows]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#6b7280', font: { size: 9 }, maxRotation: 0 },
      },
      y: {
        grid: { color: 'rgba(15,23,42,0.07)' },
        ticks: { color: '#6b7280', font: { size: 9 }, maxTicksLimit: 5 },
      },
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
                <div className="hist-kpi-sub">
                  {summary.period.start_date} → {summary.period.end_date}
                </div>
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

            {/* Chart */}
            <div className="hist-chart-card">
              <div className="hist-chart-header">
                <span className="hist-chart-title">Tendance — 14 derniers jours</span>
                <span className="hist-chart-badge">{rows.length} jours</span>
              </div>
              <div className="hist-chart-wrap">
                <Bar data={chartData} options={chartOptions} />
              </div>
            </div>

            {/* Table → liste de cartes */}
            <div className="hist-section-header">
              <span className="hist-section-title">Détail journalier</span>
            </div>

            <div className="hist-row-list">
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

            <div style={{ height: 16 }} />
          </>
        )}

      </IonContent>
    </IonPage>
  );
};

export default Historique;