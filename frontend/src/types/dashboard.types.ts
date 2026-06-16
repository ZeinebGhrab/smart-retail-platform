// ============================================================
// src/types/dashboard.types.ts — Types partagés Dashboard / SSE
// ============================================================

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface AlertItem {
  id: number;
  severity: AlertSeverity;
  title: string;
  subtitle: string;
  time: string;
  unread: boolean;
}

export type NotifIconType = 'green' | 'red' | 'amber' | 'blue' | '';

export interface NotificationItem {
  id: number;
  icon: string;
  iconType: NotifIconType;
  title: string;
  msg: string;
  time: string;
  unread: boolean;
  isPrediction?: boolean;
}

// ── Payload reçu via SSE (event: llm_report) depuis N8N ─────
// Correspond au payload posté par N8N sur POST /api/daily-report/
// et rediffusé en temps réel sur GET /api/prediction/stream/
export interface PredictionDetail {
  visiteurs_prevus: number;
  profil_dominant: string;
  niveau_affluence: string;
  heure_pointe: string;
}

export interface PredictionData {
  type: 'llm_report';
  date: string;
  generated_at: string;
  message: string;
  prediction: PredictionDetail;
}