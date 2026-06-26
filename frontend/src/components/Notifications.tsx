import React, { useState, useEffect, useRef } from 'react';
import { IonBadge, IonIcon, IonSpinner } from '@ionic/react';
import { notificationsOutline, closeOutline, chevronBackOutline, calendarOutline, timeOutline, peopleOutline, trendingUpOutline } from 'ionicons/icons';
import { useHistory } from 'react-router-dom';
import { sendToChat } from '../services/chatBridge';
import './Notifications.css';

interface Notification {
  id: number;
  title?: string;
  date: string;
  generated_at: string;
  visiteurs_prevus: number;
  profil_dominant: string;
  niveau_affluence: string;
  heure_pointe: string;
  message: string;
  model: string;
  type: string;
  is_read: boolean;
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

const fmtDateShort = (s: string) => {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
};

const lvlColor = (n: string) => {
  if (!n) return '#64748b';
  const l = n.toLowerCase();
  if (l === 'very_high' || l.includes('très')) return '#dc2626';
  if (l === 'high' || l.includes('élevé') || l.includes('eleve')) return '#ea580c';
  if (l === 'medium' || l.includes('modéré') || l.includes('modere')) return '#b45309';
  return '#059669';
};

const lvlLabel = (n: string) => {
  const map: Record<string, string> = {
    low: 'Faible', medium: 'Modéré', high: 'Élevé', very_high: 'Très élevé',
  };
  return map[n] ?? n;
};

async function fetchHistory(): Promise<Notification[]> {
  try {
    const r = await fetch(`${API}/notifications/history/`);
    if (r.ok) {
      const j = await r.json();
      const arr = Array.isArray(j) ? j : (j?.results ?? []);
      return arr;
    }
  } catch {}
  return [];
}

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

async function fetchNotificationDetail(id: number): Promise<Notification | null> {
  try {
    const r = await fetch(`${API}/notifications/${id}/`);
    if (r.ok) return await r.json();
  } catch {}
  return null;
}

// ─── Vue détail d'une notification ──────────────────────────────────────────
const NotificationDetail: React.FC<{
  notif: Notification;
  onBack: () => void;
}> = ({ notif, onBack }) => {
  const history = useHistory();

  const handleAskIA = () => {
    const msg = `Analyse cette prédiction du ${fmtDate(notif.date)} :\n${notif.message}\n\nVisiteurs prévus : ${notif.visiteurs_prevus} · Profil : ${notif.profil_dominant} · Heure de pointe : ${notif.heure_pointe} · Niveau : ${notif.niveau_affluence}`;
    sendToChat(msg);
    history.push('/chat');
  };

  return (
    <div className="notif-detail-view">
      <div className="notif-detail-header">
        <button className="notif-back-btn" onClick={onBack}>
          <IonIcon icon={chevronBackOutline} />
          <span>Historique</span>
        </button>
      </div>

      <div className="notif-detail-body">
        {/* Titre + date */}
        <div className="notif-detail-title">
          {notif.title || `Rapport IA – ${fmtDate(notif.date)}`}
        </div>
        <div className="notif-detail-meta">
          <span><IonIcon icon={calendarOutline} /> {fmtDate(notif.date)}</span>
          <span><IonIcon icon={timeOutline} /> Généré à {fmtTime(notif.generated_at)}</span>
        </div>

        {/* Métriques clés */}
        <div className="notif-detail-chips">
          <div className="notif-chip">
            <IonIcon icon={peopleOutline} />
            <span>{notif.visiteurs_prevus} visiteurs</span>
          </div>
          <div className="notif-chip">
            <IonIcon icon={timeOutline} />
            <span>Pic {notif.heure_pointe}</span>
          </div>
          <div
            className="notif-chip notif-chip-level"
            style={{ color: lvlColor(notif.niveau_affluence), borderColor: lvlColor(notif.niveau_affluence) }}
          >
            <IonIcon icon={trendingUpOutline} />
            <span>{lvlLabel(notif.niveau_affluence)}</span>
          </div>
          <div className="notif-chip">
            <span>👤 {notif.profil_dominant}</span>
          </div>
        </div>

        {/* Message LLM complet en paragraphes */}
        <div className="notif-detail-message">
          {(notif.message ?? '').split('\n').map((line, i) => {
            if (!line.trim()) return <br key={i} />;
            if (line.startsWith('**') && line.endsWith('**'))
              return <p key={i} className="notif-msg-heading">{line.replace(/\*\*/g, '')}</p>;
            if (line.startsWith('---'))
              return <hr key={i} className="notif-msg-separator" />;
            if (line.startsWith('- '))
              return <p key={i} className="notif-msg-bullet">• {line.slice(2)}</p>;
            return <p key={i} className="notif-msg-line">{line}</p>;
          })}
        </div>

        {/* Footer */}
        <div className="notif-detail-footer">
          <span className="notif-card-model">🤖 {(notif.model ?? 'llama3.2').split(':')[0]}</span>
          <button className="notif-ask-ia-btn" onClick={handleAskIA}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2" />
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Demander à l'IA
          </button>
        </div>
      </div>
    </div>
  );
};

// ─── Panel principal : liste historique ─────────────────────────────────────
const NotificationPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [list, setList] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Notification | null>(null);

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

  const handleSelect = async (notif: Notification) => {
    // Fetch full detail (list serializer omits message/model/heure_pointe/profil_dominant)
    const detail = await fetchNotificationDetail(notif.id);
    const full = detail ?? notif;
    if (!notif.is_read) {
      await markNotificationAsRead(notif.id);
      setList(prev => prev.map(n => n.id === notif.id ? { ...n, is_read: true } : n));
      setSelected({ ...full, is_read: true });
    } else {
      setSelected(full);
    }
  };

  // Vue détail
  if (selected) {
    return (
      <div className="notif-panel">
        <NotificationDetail notif={selected} onBack={() => setSelected(null)} />
      </div>
    );
  }

  // Vue liste
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
                className={`notif-row ${i === 0 ? 'notif-row-latest' : ''} ${!n.is_read ? 'notif-row-unread' : ''}`}
                onClick={() => handleSelect(n)}
              >
                <div className="notif-row-left">
                  {!n.is_read && <div className="notif-unread-dot" />}
                  <div className="notif-row-icon">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="#2563eb" strokeWidth="2" />
                      <path d="M12 6v6l4 2" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div className="notif-row-text">
                    <div className="notif-row-title">
                      {n.title || `Rapport IA – ${fmtDateShort(n.date)}`}
                    </div>
                    <div className="notif-row-sub">
                      {fmtDate(n.date)} · {fmtTime(n.generated_at)}
                    </div>
                  </div>
                </div>
                <div className="notif-row-right">
                  <span
                    className="notif-level"
                    style={{ color: lvlColor(n.niveau_affluence), borderColor: lvlColor(n.niveau_affluence) }}
                  >
                    {lvlLabel(n.niveau_affluence)}
                  </span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ color: '#94a3b8', flexShrink: 0 }}>
                    <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Bell ────────────────────────────────────────────────────────────────────
interface BellProps {
  externalUnread?: number;
  onOpen?: () => void;
}

export const NotificationBell: React.FC<BellProps> = ({ externalUnread, onOpen }) => {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);

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
        onClick={() => { setOpen(true); setUnread(0); onOpen?.(); }}
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