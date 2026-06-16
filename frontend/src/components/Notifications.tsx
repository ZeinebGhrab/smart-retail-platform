import React, { useState, useEffect, useRef } from 'react';
import {
  IonPage, IonContent, IonBadge,
  IonIcon, IonSpinner,
} from '@ionic/react';
import { notificationsOutline, closeOutline, chevronDownOutline, chevronUpOutline } from 'ionicons/icons';
import './Notifications.css';

// ── Types ─────────────────────────────────────────────────
interface Notification {
  id: number;
  date: string;
  generated_at: string;
  visiteurs_prevus: number;
  profil_dominant: string;
  niveau_affluence: string;
  heure_pointe: string;
  message: string;
  model: string;
  type: string;
}

// ── Helpers ───────────────────────────────────────────────
const API = import.meta.env?.VITE_API_URL || 'http://localhost:8000/api';
const POLL_MS = 5000;

function fmtTime(iso: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${d.getHours()}h${String(d.getMinutes()).padStart(2, '0')}`;
}

function fmtDate(str: string) {
  if (!str) return '—';
  const d = new Date(str);
  return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
}

function levelColor(niveau: string): string {
  if (!niveau) return '#64748b';
  const n = niveau.toLowerCase();
  if (n.includes('très')) return '#f87171';
  if (n.includes('élevé') || n.includes('eleve')) return '#fb923c';
  if (n.includes('modéré') || n.includes('modere')) return '#fbbf24';
  return '#34d399';
}

// ── Fetch helpers ─────────────────────────────────────────
async function fetchLatest(): Promise<Notification | null> {
  try {
    const r = await fetch(`${API}/notifications/latest/`);
    if (r.ok) return await r.json();
  } catch {}
  try {
    const r = await fetch(`http://localhost:8001/latest_notification.json?t=${Date.now()}`);
    if (r.ok) return await r.json();
  } catch {}
  return null;
}

async function fetchHistory(): Promise<Notification[]> {
  try {
    const r = await fetch(`${API}/notifications/history/`);
    if (r.ok) return await r.json();
  } catch {}
  try {
    const r = await fetch(`http://localhost:8001/notifications_history.json?t=${Date.now()}`);
    if (r.ok) return await r.json();
  } catch {}
  return [];
}

// ── Notification Panel ────────────────────────────────────
interface PanelProps {
  onClose: () => void;
}

const NotificationPanel: React.FC<PanelProps> = ({ onClose }) => {
  const [latest, setLatest] = useState<Notification | null>(null);
  const [history, setHistory] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(0);
  const lastId = useRef<number | null>(null);

  const load = async () => {
    const [l, h] = await Promise.all([fetchLatest(), fetchHistory()]);
    if (l) { setLatest(l); lastId.current = l.id; }
    setHistory(h);
    setLoading(false);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="notif-panel">
      {/* Panel header */}
      <div className="notif-panel-header">
        <div className="notif-panel-title">
          <IonIcon icon={notificationsOutline} />
          Notifications IA
          {history.length > 0 && (
            <span className="notif-count-badge">{history.length}</span>
          )}
        </div>
        <button className="notif-close-btn" onClick={onClose}>
          <IonIcon icon={closeOutline} />
        </button>
      </div>

      {/* Content */}
      <div className="notif-panel-body">
        {loading ? (
          <div className="notif-loading">
            <IonSpinner name="crescent" />
            <p>Chargement…</p>
          </div>
        ) : history.length === 0 ? (
          <div className="notif-empty">
            <span className="notif-empty-icon">🔔</span>
            <p>Aucune notification pour le moment.</p>
            <p className="notif-empty-sub">La prochaine arrivera à 6h00.</p>
          </div>
        ) : (
          <div className="notif-list">
            {history.map((n, i) => (
              <div
                key={n.id}
                className={`notif-card ${i === 0 ? 'notif-card-latest' : ''}`}
              >
                {/* Card header */}
                <div
                  className="notif-card-header"
                  onClick={() => setExpanded(expanded === i ? null : i)}
                >
                  <div className="notif-card-left">
                    <div className="notif-card-icon">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#60a5fa" strokeWidth="2"/>
                        <path d="M12 6v6l4 2" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round"/>
                      </svg>
                    </div>
                    <div>
                      <div className="notif-card-date">{fmtDate(n.date)}</div>
                      <div className="notif-card-time">Généré à {fmtTime(n.generated_at)}</div>
                    </div>
                  </div>
                  <div className="notif-card-right">
                    <span
                      className="notif-level"
                      style={{ color: levelColor(n.niveau_affluence), borderColor: levelColor(n.niveau_affluence) }}
                    >
                      {n.niveau_affluence}
                    </span>
                    <IonIcon
                      icon={expanded === i ? chevronUpOutline : chevronDownOutline}
                      style={{ color: '#64748b', fontSize: '14px' }}
                    />
                  </div>
                </div>

                {/* Visitors strip */}
                <div className="notif-card-strip">
                  <div className="notif-strip-item">
                    <span className="notif-strip-label">Visiteurs prévus</span>
                    <span className="notif-strip-value">{n.visiteurs_prevus}</span>
                  </div>
                  <div className="notif-strip-item">
                    <span className="notif-strip-label">Profil</span>
                    <span className="notif-strip-value">{n.profil_dominant}</span>
                  </div>
                  <div className="notif-strip-item">
                    <span className="notif-strip-label">Pointe</span>
                    <span className="notif-strip-value">{n.heure_pointe}</span>
                  </div>
                </div>

                {/* Expanded message */}
                {expanded === i && (
                  <div className="notif-card-message">
                    <p>{n.message}</p>
                    <div className="notif-card-model">
                      🤖 {n.model?.split(':')[0] ?? 'llama3.2'}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Bell Icon (à placer dans le header du Dashboard) ─────
export const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const lastId = useRef<number | null>(null);

  useEffect(() => {
    const check = async () => {
      const latest = await fetchLatest();
      if (latest && latest.id !== lastId.current) {
        if (lastId.current !== null) setUnread(u => u + 1);
        lastId.current = latest.id;
      }
    };
    check();
    const t = setInterval(check, POLL_MS);
    return () => clearInterval(t);
  }, []);

  const handleOpen = () => {
    setOpen(true);
    setUnread(0);
  };

  return (
    <div className="notif-bell-wrapper">
      <button className="notif-bell-btn" onClick={handleOpen} aria-label="Notifications">
        <IonIcon icon={notificationsOutline} />
        {unread > 0 && (
          <IonBadge className="notif-bell-badge">{unread}</IonBadge>
        )}
      </button>

      {open && (
        <>
          <div className="notif-overlay" onClick={() => setOpen(false)} />
          <NotificationPanel onClose={() => setOpen(false)} />
        </>
      )}
    </div>
  );
};

export default NotificationBell;