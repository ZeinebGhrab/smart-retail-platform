import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  IonPage,
  IonContent,
} from '@ionic/react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

import { useSSEPrediction } from '../hooks/useSSEPrediction';
import {
  AlertItem,
  NotificationItem,
  PredictionData,
  NotifIconType,
} from '../types/dashboard.types';
import './Dashboard.css';
// FIX: import nommé — NotificationBell est un named export dans Notifications.tsx
import { NotificationBell } from '../components/Notifications';
import { useHistory } from 'react-router-dom';
import { sendToChat } from '../services/chatBridge';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip);

const INTRADAY_LABELS    = ['8h','9h','10h','11h','12h','13h','14h','15h','16h','17h','18h','19h','20h'];
const INTRADAY_TODAY     = [0, 45, 120, 210, 290, 340, 390, 450, 490, 430, 360, 250, 150];
const INTRADAY_YESTERDAY = [0, 30, 100, 180, 260, 310, 360, 420, 440, 400, 320, 210, 120];

const INITIAL_ALERTS: AlertItem[] = [
  { id: 1, severity: 'critical', title: 'Affluence critique — Porte Nord',  subtitle: 'Capacité dépassée de 18% · Zone A',      time: 'Il y a 3 min',       unread: true  },
  { id: 2, severity: 'warning',  title: "Caisse 4 — file d'attente longue", subtitle: '8 personnes · Ouvrir caisse 5',          time: 'Il y a 7 min',       unread: true  },
  { id: 3, severity: 'info',     title: 'Prédiction reçue — n8n',           subtitle: 'Rapport quotidien généré par Llama 3.2', time: "Aujourd'hui, 06:00", unread: false },
];

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  { id: 1, icon: 'brain',         iconType: 'green' as NotifIconType, title: 'Rapport IA — Prédiction quotidienne', msg: 'En attente du prochain rapport n8n…',                              time: "Aujourd'hui, 06:00", unread: false, isPrediction: true },
  { id: 2, icon: 'users',         iconType: 'red'   as NotifIconType, title: 'Affluence critique — Porte Nord',     msg: 'Capacité dépassée de 18%. Renforcement du personnel recommandé.',   time: 'Il y a 3 min',       unread: true  },
  { id: 3, icon: 'cash-register', iconType: 'amber' as NotifIconType, title: 'Caisse 4 — file longue',              msg: '8 personnes en attente. Ouvrir caisse 5 immédiatement.',            time: 'Il y a 7 min',       unread: true  },
  { id: 4, icon: 'trending-up',   iconType: ''      as NotifIconType, title: 'Conversion +2.1% ce matin',           msg: 'Le taux de conversion dépasse la moyenne hebdomadaire.',            time: 'Il y a 32 min',      unread: true  },
  { id: 5, icon: 'alert-circle',  iconType: 'amber' as NotifIconType, title: 'Stock faible — Rayon enfants',        msg: 'Réassort nécessaire pour 4 références.',                            time: 'Il y a 1h',          unread: false },
];

// FIX: ces pills filtrent des sections de CETTE page (pas une navigation
// vers d'autres écrans) — limitées aux sections réellement présentes
// pour ne pas donner l'illusion de liens cassés.
const NAV_TABS = ["Vue d'ensemble", 'Alertes', 'Prédiction IA'];
const DAYS     = ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
const MONTHS   = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];

function todayLabel() {
  const d = new Date();
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}
function timeLabel() {
  const d = new Date();
  return `${d.getHours()}h${d.getMinutes().toString().padStart(2, '0')}`;
}

interface KpiCardProps { icon: string; label: string; value: string; delta: string; deltaNeg?: boolean; }
const KpiCard: React.FC<KpiCardProps> = ({ icon, label, value, delta, deltaNeg }) => (
  <div className="db-kpi-card">
    <div className="db-kpi-label"><span className={`db-icon ti ti-${icon}`} aria-hidden="true" />{label}</div>
    <div className="db-kpi-value">{value}</div>
    <div className={`db-kpi-delta ${deltaNeg ? 'neg' : ''}`}>{delta}</div>
  </div>
);

interface AlertRowProps { alert: AlertItem }
const AlertRow: React.FC<AlertRowProps> = ({ alert }) => {
  const iconMap:  Record<string, string> = { critical: 'users-group', warning: 'cash-register', info: 'chart-line' };
  const colorMap: Record<string, string> = { critical: 'red',         warning: 'amber',         info: 'blue'       };
  return (
    <div className={`db-alert-item ${alert.severity}`}>
      <div className={`db-alert-icon ${colorMap[alert.severity]}`}>
        <span className={`ti ti-${iconMap[alert.severity]}`} aria-hidden="true" />
      </div>
      <div className="db-alert-body">
        <div className="db-alert-title">{alert.title}</div>
        <div className="db-alert-sub">{alert.subtitle}</div>
        <div className="db-alert-time">{alert.time}</div>
      </div>
      <div className={`db-alert-dot ${alert.unread ? '' : 'seen'}`} />
    </div>
  );
};

const Dashboard: React.FC = () => {
  const history = useHistory();
  const [activeTab,     setActiveTab]     = useState("Vue d'ensemble");
  const [notifOpen,     setNotifOpen]     = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);
  const [alerts,        setAlerts]        = useState<AlertItem[]>(INITIAL_ALERTS);
  const [toastData,     setToastData]     = useState<{ msg: string; time: string } | null>(null);
  const [prediction,    setPrediction]    = useState<PredictionData | null>(null);

  // FIX: initialisé au nombre réel de notifications unread, pas un magic number
  const [badgeCount, setBadgeCount] = useState(
    INITIAL_NOTIFICATIONS.filter(n => n.unread).length
  );

  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { prediction: ssePrediction, isConnected } = useSSEPrediction();

  // FIX: refs de section — les pills de filtre scrollent désormais
  // réellement vers la section correspondante au lieu de ne rien faire.
  const contentRef    = useRef<HTMLIonContentElement>(null);
  const overviewRef   = useRef<HTMLDivElement>(null);
  const predictionRef = useRef<HTMLDivElement>(null);
  const alertsRef     = useRef<HTMLDivElement>(null);

  const handleTabClick = useCallback((tab: string) => {
    setActiveTab(tab);
    const targetMap: Record<string, React.RefObject<HTMLDivElement>> = {
      "Vue d'ensemble": overviewRef,
      'Prédiction IA': predictionRef,
      'Alertes': alertsRef,
    };
    const target = targetMap[tab]?.current;
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const handleNewPrediction = useCallback((data: PredictionData) => {
    if (!data || !data.prediction) return;

    setPrediction(data);

    setNotifications(prev => prev.map(n =>
      n.isPrediction
        ? { ...n, msg: data.message ?? '', time: timeLabel(), unread: true }
        : n
    ));

    setAlerts(prev => prev.map(a =>
      a.id === 3
        ? { ...a, subtitle: `Rapport du ${data.date} · Llama 3.2`, time: timeLabel(), unread: true }
        : a
    ));

    // FIX: incrémenter le badge de la cloche lors d'une nouvelle prédiction SSE
    setBadgeCount(prev => prev + 1);

    const shortMsg = data.message
      ? data.message.substring(0, 90) + '…'
      : 'Nouvelle prédiction disponible.';
    setToastData({ msg: shortMsg, time: timeLabel() });
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastData(null), 7000);
  }, []);

  useEffect(() => {
    if (ssePrediction) handleNewPrediction(ssePrediction);
  }, [ssePrediction, handleNewPrediction]);

  useEffect(() => () => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
  }, []);

  // FIX: fonction centralisée — ouvre le panel ET remet le badge à 0
  const handleNotifClick = (n: NotificationItem) => {
    const msg = `${n.title} : ${n.msg}`;
    sendToChat(msg);
    setNotifOpen(false);
    history.push('/chat');
  };

  const handleNotifOpen = useCallback(() => {
    setNotifOpen(true);
    setBadgeCount(0);
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
  }, []);

  const chartData = {
    labels: INTRADAY_LABELS,
    datasets: [
      {
        label: "Aujourd'hui",
        data: INTRADAY_TODAY,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,0.08)',
        borderWidth: 2, pointRadius: 0, tension: 0.4, fill: true,
      },
      {
        label: 'Hier',
        data: INTRADAY_YESTERDAY,
        borderColor: 'rgba(21,128,61,0.6)',
        borderWidth: 1.5, pointRadius: 0, tension: 0.4, fill: false,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#6b7280', font: { size: 9 }, maxRotation: 0 } },
      y: { grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#6b7280', font: { size: 9 }, maxTicksLimit: 5 } },
    },
  } as const;

  return (
    <IonPage className="db-page">

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="db-header">
        <div className="db-header-top">
          <div>
            <div className="db-store-name">Kiabi — Vélizy 2</div>
            <div className="db-store-date">{todayLabel()}</div>
            <div className="db-live-badge">
              <span className="db-live-dot" />
              En direct
              {!isConnected && <span className="db-sse-status disconnected"> · SSE hors ligne</span>}
            </div>
          </div>

          {/*
            FIX: passer externalUnread + onOpen pour que la cloche soit
            pilotée par le badgeCount du Dashboard, pas par son propre polling
          */}
          <NotificationBell
            externalUnread={badgeCount}
            onOpen={handleNotifOpen}
          />
        </div>

        <div className="db-tab-row">
          {NAV_TABS.map(tab => (
            <button
              key={tab}
              className={`db-tab-pill ${activeTab === tab ? 'active' : ''}`}
              onClick={() => handleTabClick(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content ───────────────────────────────────────────────── */}
      <IonContent className="db-content" ref={contentRef}>

        {/* KPIs */}
        <div className="db-kpi-grid" ref={overviewRef}>
          <KpiCard icon="users"          label="Visiteurs"          value="1 247"    delta="+12% vs hier" />
          <KpiCard icon="trending-up"    label="Chiffre d'affaires" value="14 320 €" delta="+8% vs J-7" />
          <KpiCard icon="percentage"     label="Taux de conversion" value="23.4%"    delta="+2.1%" />
          <KpiCard
            icon="alert-triangle"
            label="Alertes actives"
            value={String(alerts.length)}
            delta={`${alerts.filter(a => a.unread).length} non traitées`}
            deltaNeg
          />
        </div>

        {/* Chart */}
        <div className="db-chart-card">
          <div className="db-chart-header">
            <span className="db-chart-title">Fréquentation intraday</span>
            <button className="db-export-btn">
              <span className="ti ti-upload" aria-hidden="true" /> Export
            </button>
          </div>
          <div className="db-chart-wrap">
            <Line data={chartData} options={chartOptions} />
          </div>
          <div className="db-chart-legend">
            <div className="db-legend-item"><span className="db-legend-line blue" /> Aujourd'hui</div>
            <div className="db-legend-item"><span className="db-legend-line green" /> Hier</div>
          </div>
        </div>

        {/* Prediction card SSE */}
        <div ref={predictionRef} />
        {prediction && prediction.prediction && (
          <div className="db-pred-card">
            <div className="db-pred-header">
              <span className="db-pred-title">
                <span className="ti ti-brain" aria-hidden="true" /> Prédiction IA — n8n
              </span>
              <span className="db-pred-badge">Nouveau</span>
            </div>
            <div className="db-pred-grid">
              <div className="db-pred-item">
                <div className="db-pred-item-label">Visiteurs prévus</div>
                <div className="db-pred-item-value">{prediction.prediction.visiteurs_prevus ?? '—'}</div>
              </div>
              <div className="db-pred-item">
                <div className="db-pred-item-label">Profil dominant</div>
                <div className="db-pred-item-value">{prediction.prediction.profil_dominant ?? '—'}</div>
              </div>
              <div className="db-pred-item">
                <div className="db-pred-item-label">Affluence</div>
                <div className="db-pred-item-value">{prediction.prediction.niveau_affluence ?? '—'}</div>
              </div>
              <div className="db-pred-item">
                <div className="db-pred-item-label">Heure de pointe</div>
                <div className="db-pred-item-value">{prediction.prediction.heure_pointe ?? '—'}</div>
              </div>
            </div>
            <p className="db-pred-msg">{prediction.message}</p>
          </div>
        )}

        {/* Alertes */}
        <div className="db-section-header" ref={alertsRef}>
          <span className="db-section-title">Alertes en direct</span>
          <button className="db-voir-tout">Voir tout</button>
        </div>
        <div className="db-alert-list">
          {alerts.map(a => <AlertRow key={a.id} alert={a} />)}
        </div>
        <div style={{ height: 16 }} />

      </IonContent>

      {/* ── Notification Panel (alertes locales Dashboard) ─────── */}
      {notifOpen && (
        <div
          className="db-notif-overlay"
          onClick={e => e.target === e.currentTarget && setNotifOpen(false)}
        >
          <div className="db-notif-panel" role="dialog" aria-label="Notifications">
            <div className="db-notif-panel-header">
              <span className="db-notif-panel-title">Notifications</span>
              <button className="db-notif-close" onClick={() => setNotifOpen(false)} aria-label="Fermer">
                <span className="ti ti-x" aria-hidden="true" />
              </button>
            </div>
            <div className="db-notif-scroll">
              {notifications.map(n => (
                <div key={n.id} className="db-notif-item" onClick={() => handleNotifClick(n)} style={{ cursor: 'pointer' }}>
                  <div className={`db-notif-icon ${n.iconType}`}>
                    <span className={`ti ti-${n.icon}`} aria-hidden="true" />
                  </div>
                  <div className="db-notif-body">
                    <div className="db-notif-item-title">{n.title}</div>
                    <div className="db-notif-item-msg">{n.msg}</div>
                    <div className="db-notif-item-time">{n.time}</div>
                  </div>
                  {n.unread && <div className="db-notif-unread-dot" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── SSE Toast ─────────────────────────────────────────────── */}
      {toastData && (
        <div className="db-sse-toast" role="alert" onClick={() => { if (toastData) { sendToChat(`Rapport IA n8n : ${toastData.msg}`); setToastData(null); history.push('/chat'); } }} style={{ cursor: 'pointer' }}>
          <div className="db-toast-header">
            <div className="db-toast-label">
              <span className="ti ti-brain" aria-hidden="true" /> ShopAnalytics — n8n
            </div>
            <button className="db-toast-close" onClick={() => setToastData(null)} aria-label="Fermer">
              <span className="ti ti-x" aria-hidden="true" />
            </button>
          </div>
          <div className="db-toast-msg">{toastData.msg}</div>
          <div className="db-toast-time">{toastData.time}</div>
        </div>
      )}

    </IonPage>
  );
};

export default Dashboard;