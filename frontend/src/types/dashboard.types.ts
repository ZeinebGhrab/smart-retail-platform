// ─── Dashboard Types ─────────────────────────────────────────────────────────

export interface KPIData {
  visitors: number;
  visitorsVsYesterday: number;
  revenue: number;
  revenueVsLastWeek: number;
  conversionRate: number;
  conversionDelta: number;
  activeAlerts: number;
  untreatedAlerts: number;
}

export interface IntradayPoint {
  hour: string;
  today: number;
  yesterday: number;
}

export interface PredictionData {
  type: string;
  date: string;
  generated_at: string;
  message: string;
  prediction: {
    visiteurs_prevus: number;
    profil_dominant: string;
    niveau_affluence: string;
    heure_pointe: string;
  };
}

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface AlertItem {
  id: number;
  severity: AlertSeverity;
  title: string;
  subtitle: string;
  time: string;
  unread: boolean;
}

export type NotifIconType = 'red' | 'amber' | 'green' | 'blue' | '';

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