import React, { useState, useEffect, useRef } from 'react';
import { IonBadge, IonIcon, IonSpinner } from '@ionic/react';
import { notificationsOutline, closeOutline, chevronDownOutline, chevronUpOutline } from 'ionicons/icons';
import { useHistory } from 'react-router-dom';
import { sendToChat } from '../services/chatBridge';
import './Notifications.css';

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
  is_read: boolean; // ← 
}

const API = ((import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api') + '/predictions';
const POLL_MS = 5000;

const fmtTime = (iso: string) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${d.getHours()}h${String(d.getMinutes()).padStart(2, '0')}`;
};

const fmtDate = (s: string) => {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
};

const lvlColor = (n: string) => {
  if (!n) return '#64748b';
  const l = n.toLowerCase();
  if (l.includes('très')) return '#dc2626';
  if (l.includes('élevé') || l.includes('eleve')) return '#ea580c';
  if (l.includes('modéré') || l.includes('modere')) return '#b45309';
  return '#059669';
};

// Récupérer la dernière notification
async function fetchLatest(): Promise<Notification | null> {
  try {
    const r = await fetch(`${API}/notifications/latest/`);
    if (r.ok) {
      const j = await r.json();
      if (j?.id !== undefined) return j;
    }
  } catch {}
  return null;
}

// Récupérer l'historique (du plus récent au plus ancien, déjà trié par le backend)
async function fetchHistory(): Promise<Notification[]> {
  try {
    const r = await fetch(`${API}/notifications/history/`);
    if (r.ok) {
      const j = await r.json();
      return Array.isArray(j) ? j : [];
    }
  } catch {}
  return [];
}

// Compter les notifications non lues
async function fetchUnreadCount(): Promise<number> {
  try {
    const r = await fetch(`${API}/notifications/unread-count/`);
    if (r.ok) {
      const j = await r.json();
      return j.unread_count ?? 0;
    }
  } catch {}
  return 0;
}

// Marquer une notification comme lue
async function markNotificationAsRead(notificationId: number): Promise<boolean> {
  try {
    const r = await fetch(`${API}/notifications/${notificationId}/mark-read/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return r.ok;
  } catch {}
  return false;
}

const NotificationPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const history = useHistory();
  const [list, setList] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(0);

  useEffect(() => {
    const load = async () => {
      const h = await fetchHistory();
      setList(h);
      setLoading(false);
    };
    load();
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, []);

  const handleAskIA = (n: Notification) => {
    const msg = `Analyse cette prédiction du ${fmtDate(n.date)} :\n${n.message}\n\nVisiteurs prévus : ${n.visiteurs_prevus} · Profil : ${n.profil_dominant} · Heure de pointe : ${n.heure_pointe} · Niveau : ${n.niveau_affluence}`;
    sendToChat(msg);
    onClose();
    history.push('/chat');
  };

  // Marquer comme lue au clic
  const handleExpandNotification = async (index: number) => {
    const n = list[index];
    if (n && !n.is_read) {
      const success = await markNotificationAsRead(n.id);
      if (success) {
        const updated = [...list];
        updated[index].is_read = true;
        setList(updated);
      }
    }
    setExpanded(expanded === index ? null : index);
  };

  return (
    <div className="notif-panel">
      <div className="notif-panel-header">
        <div className="notif-panel-title">
          <IonIcon icon={notificationsOutline} />
          Notifications IA
          {list.length > 0 && <span className="notif-count-badge">{list.length}</span>}
        </div>
        <button className="notif-close-btn" onClick={onClose}>
          <IonIcon icon={closeOutline} />
        </button>
      </div>

      <div className="notif-panel-body">
        {loading ? (
          <div className="notif-loading">
            <IonSpinner name="crescent" />
            <p>Chargement…</p>
          </div>
        ) : list.length === 0 ? (
          <div className="notif-empty">
            <span className="notif-empty-icon">🔔</span>
            <p>Aucune notification pour le moment.</p>
            <p className="notif-empty-sub">La prochaine arrivera à 6h00.</p>
          </div>
        ) : (
          <div className="notif-list">
            {list.map((n, i) => (
              <div
                key={n.id}
                className={`notif-card ${i === 0 ? 'notif-card-latest' : ''} ${
                  !n.is_read ? 'notif-card-unread' : ''
                }`}
              >
                <div className="notif-card-header" onClick={() => handleExpandNotification(i)}>
                  <div className="notif-card-left">
                    {!n.is_read && <div className="notif-unread-indicator" />}
                    <div className="notif-card-icon">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#2563eb" strokeWidth="2" />
                        <path d="M12 6v6l4 2" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" />
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
                      style={{
                        color: lvlColor(n.niveau_affluence),
                        borderColor: lvlColor(n.niveau_affluence),
                      }}
                    >
                      {n.niveau_affluence}
                    </span>
                    <IonIcon
                      icon={expanded === i ? chevronUpOutline : chevronDownOutline}
                      style={{ color: '#64748b', fontSize: '14px' }}
                    />
                  </div>
                </div>

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

                {expanded === i && (
                  <div className="notif-card-message">
                    <p>{n.message}</p>
                    <div className="notif-card-footer">
                      <div className="notif-card-model">🤖 {n.model?.split(':')[0] ?? 'llama3.2'}</div>
                      <button className="notif-ask-ia-btn" onClick={() => handleAskIA(n)}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                          <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
                          <path
                            d="M4 20c0-4 3.6-7 8-7s8 3 8 7"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                        </svg>
                        Demander à l'IA
                      </button>
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

interface BellProps {
  externalUnread?: number;
  onOpen?: () => void;
}

export const NotificationBell: React.FC<BellProps> = ({ externalUnread, onOpen }) => {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const lastId = useRef<number | null>(null);

  useEffect(() => {
    if (externalUnread !== undefined) return;

    const check = async () => {
      const count = await fetchUnreadCount();
      setUnread(count);
    };

    check();
    const t = setInterval(check, POLL_MS);
    return () => clearInterval(t);
  }, [externalUnread]);

  const displayUnread = externalUnread !== undefined ? externalUnread : unread;

  return (
    <div className="notif-bell-wrapper">
      <button
        className="notif-bell-btn"
        onClick={() => {
          setOpen(true);
          setUnread(0);
          onOpen?.();
        }}
        aria-label="Notifications"
      >
        <IonIcon icon={notificationsOutline} />
        {displayUnread > 0 && <IonBadge className="notif-bell-badge">{displayUnread}</IonBadge>}
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