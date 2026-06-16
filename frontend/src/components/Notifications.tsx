// ============================================================
// src/components/Notifications.tsx — Cloche de notification
// Affiche un badge avec le nombre de notifications non lues
// (récupérées depuis GET /api/notifications/latest/ au montage).
// ============================================================

import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../services/api';
import './Notifications.css';

interface LatestNotification {
  message?: string;
  date?: string;
}

const NotificationBell: React.FC = () => {
  const [hasUnread, setHasUnread] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetch(`${API_BASE_URL}/notifications/latest/`)
      .then(res => (res.ok ? res.json() : null))
      .then((data: LatestNotification | null) => {
        if (!cancelled && data && data.message) setHasUnread(true);
      })
      .catch(() => {
        // Backend indisponible — la cloche reste neutre, pas bloquant
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <button className="notif-bell-btn" aria-label="Notifications">
      <span className="ti ti-bell notif-bell-icon" aria-hidden="true" />
      {hasUnread && <span className="notif-bell-dot" />}
    </button>
  );
};

export default NotificationBell;