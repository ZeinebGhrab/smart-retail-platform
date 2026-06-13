import React, { useEffect, useState } from 'react';
import {
  IonContent,
  IonPage,
  IonHeader,
  IonToolbar,
  IonTitle,
  IonSpinner,
  IonSegment,
  IonSegmentButton,
  IonLabel,
  IonCard,
  IonCardContent,
  IonGrid,
  IonRow,
  IonCol,
} from '@ionic/react';
import {
  getSummary,
  getVisitorHistory,
  getForecast,
  SummaryResponse,
  DailyHistoryRow,
  ForecastResponse,
} from '../services/api';
import './Historique.css';

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
        // Affiche les 14 derniers jours, du plus récent au plus ancien
        setRows(historyRes.results.slice(-14).reverse());
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

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>Historique visiteurs</IonTitle>
        </IonToolbar>
        <IonToolbar>
          <IonSegment
            value={camera}
            onIonChange={(e) => setCamera(String(e.detail.value))}
          >
            <IonSegmentButton value="toutes">
              <IonLabel>Toutes</IonLabel>
            </IonSegmentButton>
            <IonSegmentButton value="Porte_nord">
              <IonLabel>Porte Nord</IonLabel>
            </IonSegmentButton>
            <IonSegmentButton value="Porte_sud">
              <IonLabel>Porte Sud</IonLabel>
            </IonSegmentButton>
          </IonSegment>
        </IonToolbar>
      </IonHeader>

      <IonContent className="ion-padding historique-content">
        {loading && (
          <div className="historique-loading">
            <IonSpinner name="crescent" />
            <p>Chargement des données…</p>
          </div>
        )}

        {error && (
          <IonCard color="danger">
            <IonCardContent>
              Impossible de contacter l'API Django ({error}). Vérifiez que le
              backend tourne sur <code>http://localhost:8000</code>.
            </IonCardContent>
          </IonCard>
        )}

        {!loading && !error && summary && (
          <>
            {/* KPIs */}
            <IonGrid className="kpi-grid">
              <IonRow>
                <IonCol size="6" sizeMd="3">
                  <IonCard className="kpi-card">
                    <IonCardContent>
                      <div className="kpi-label">Total visiteurs</div>
                      <div className="kpi-value">
                        {summary.total_visits.toLocaleString('fr-FR')}
                      </div>
                      <div className="kpi-sub">
                        {summary.period.start_date} → {summary.period.end_date}
                      </div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="6" sizeMd="3">
                  <IonCard className="kpi-card">
                    <IonCardContent>
                      <div className="kpi-label">Hommes / Femmes</div>
                      <div className="kpi-value">
                        {summary.by_gender.men.toLocaleString('fr-FR')} /{' '}
                        {summary.by_gender.women.toLocaleString('fr-FR')}
                      </div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="6" sizeMd="3">
                  <IonCard className="kpi-card">
                    <IonCardContent>
                      <div className="kpi-label">Jours d'historique</div>
                      <div className="kpi-value">{summary.period.n_days}</div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
                <IonCol size="6" sizeMd="3">
                  <IonCard className="kpi-card kpi-forecast">
                    <IonCardContent>
                      <div className="kpi-label">
                        Prévision {forecast?.target_date}
                      </div>
                      <div className="kpi-value">
                        {forecast?.predicted_visit_count.toLocaleString('fr-FR')}
                      </div>
                      <div className="kpi-sub">
                        Confiance : {forecast?.confidence}
                      </div>
                    </IonCardContent>
                  </IonCard>
                </IonCol>
              </IonRow>
            </IonGrid>

            {/* Tableau historique */}
            <h3 className="section-title">14 derniers jours</h3>
            <div className="table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Caméra</th>
                    <th>Visiteurs</th>
                    <th>Hommes</th>
                    <th>Femmes</th>
                    <th>Enfants</th>
                    <th>Ados</th>
                    <th>Adultes</th>
                    <th>Seniors</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={`${row.date}-${row.camera}`}>
                      <td>{row.date}</td>
                      <td>{row.camera}</td>
                      <td className="cell-strong">{row.visit_Count}</td>
                      <td>{row.gender_men}</td>
                      <td>{row.gender_women}</td>
                      <td>{row.age_child}</td>
                      <td>{row.age_teenager}</td>
                      <td>{row.age_adult}</td>
                      <td>{row.age_senior}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </IonContent>
    </IonPage>
  );
};

export default Historique;