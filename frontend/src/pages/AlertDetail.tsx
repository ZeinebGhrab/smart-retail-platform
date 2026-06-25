import React, { useEffect, useState } from 'react';
import { IonPage, IonContent, useIonRouter } from '@ionic/react';
import { useParams } from 'react-router-dom';
import { SecurityAlert, AlertStatus, ALERT_STATUS_LABELS } from '../services/alert';
import { fetchAlertById, qualifyAlert } from '../services/alerts';
import './AlertDetail.css';

// Les 4 options correspondent exactement aux boutons envoyés par le bot Telegram
// ("Vol confirmé (client interpellé)", "Vol confirmé (client non interpellé)",
//  "Comportement suspect", "Fausse alerte"), pour garder le même vocabulaire
// entre Telegram et l'app mobile.
const QUALIFY_OPTIONS: { status: AlertStatus; label: string }[] = [
  { status: 'vol_confirme_interpelle', label: 'Vol confirmé (client interpellé)' },
  { status: 'vol_confirme_non_interpelle', label: 'Vol confirmé (client non interpellé)' },
  { status: 'comportement_suspect', label: 'Comportement suspect' },
  { status: 'fausse_alerte', label: 'Fausse alerte' },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const AlertDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const ionRouter = useIonRouter();
  const [alert, setAlert] = useState<SecurityAlert | null>(null);
  const [loading, setLoading] = useState(true);
  const [qualifying, setQualifying] = useState<AlertStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchAlertById(id)
      .then((data) => mounted && setAlert(data))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [id]);

  const handleQualify = async (status: AlertStatus) => {
    if (!alert || alert.status !== 'en_attente') return;
    setQualifying(status);
    try {
      const updated = await qualifyAlert(alert.id, status);
      setAlert(updated);
    } finally {
      setQualifying(null);
    }
  };

  if (loading) {
    return (
      <IonPage>
        <IonContent className="alert-detail-content">
          <div className="alerts-state">Chargement…</div>
        </IonContent>
      </IonPage>
    );
  }

  if (!alert) {
    return (
      <IonPage>
        <IonContent className="alert-detail-content">
          <div className="alerts-state error">Alerte introuvable.</div>
        </IonContent>
      </IonPage>
    );
  }

  const alreadyQualified = alert.status !== 'en_attente';

  return (
    <IonPage>
      <IonContent fullscreen className="alert-detail-content">
        <div className="alert-detail-header">
          <button className="alert-back-btn" onClick={() => ionRouter.push('/alerts')} aria-label="Retour">
            <span className="ti ti-arrow-left" />
          </button>
          <h1>Alerte — {alert.cameraLabel}</h1>
        </div>

        <div className="alert-video-wrap">
          {alert.videoUrl ? (
            <video src={alert.videoUrl} controls className="alert-video" />
          ) : (
            <div className="alert-video-placeholder">
              <span className="ti ti-player-play-filled" />
            </div>
          )}
          <span className="alert-confidence-pill">{alert.confidence}%</span>
        </div>

        <div className="alert-meta-card">
          <h2>Métadonnées</h2>

          <div className="alert-meta-row">
            <span className="alert-meta-label">Caméra</span>
            <span className="alert-meta-value">
              {alert.cameraLabel} — {alert.location}
            </span>
          </div>

          <div className="alert-meta-row">
            <span className="alert-meta-label">Heure</span>
            <span className="alert-meta-value">{formatDate(alert.createdAt)}</span>
          </div>

          <div className="alert-meta-row">
            <span className="alert-meta-label">Type de geste</span>
            <span className="alert-meta-value">{alert.message}</span>
          </div>

          <div className="alert-meta-row column">
            <span className="alert-meta-label">Score de confiance</span>
            <span className="alert-meta-value">{alert.confidence}%</span>
            <div className="alert-confidence-bar">
              <div className="alert-confidence-fill" style={{ width: `${alert.confidence}%` }} />
            </div>
          </div>

          <div className="alert-meta-row">
            <span className="alert-meta-label">Référence</span>
            <span className="alert-meta-value alert-tag">{alert.rawTag}</span>
          </div>
        </div>

        <div className="alert-qualify-card">
          <h2>Qualifier cet incident</h2>

          {alreadyQualified ? (
            <p className="alert-qualified-info">
              {ALERT_STATUS_LABELS[alert.status]}
              {alert.qualifiedBy && (
                <>
                  {' '}— par <strong>{alert.qualifiedBy}</strong>
                </>
              )}
            </p>
          ) : (
            <div className="alert-qualify-grid">
              {QUALIFY_OPTIONS.map((opt) => (
                <button
                  key={opt.status}
                  className={`alert-qualify-btn qualify-${opt.status}`}
                  disabled={qualifying !== null}
                  onClick={() => handleQualify(opt.status)}
                >
                  {qualifying === opt.status ? '…' : opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </IonContent>
    </IonPage>
  );
};

export default AlertDetail;
