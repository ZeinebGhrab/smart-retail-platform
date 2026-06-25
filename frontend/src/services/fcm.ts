// ============================================================
// frontend/src/services/fcm.ts
// Service pour interagir avec les endpoints FCM du backend
// ============================================================

import axios from 'axios';
import { getAccessToken } from './auth'; 
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// export const saveFCMToken = async (token: string): Promise<void> => {
//   try {
//     const response = await axios.post(`${API_BASE_URL}/fcm-token/`, { token });
//     console.log('Token FCM sauvegardé:', response.data);
//   } catch (error) {
//     console.error('Erreur lors de la sauvegarde du token FCM:', error);
//     throw error;
//   }
// };
export const saveFCMToken = async (token: string): Promise<void> => {
  try {
    const accessToken = getAccessToken();
    const response = await axios.post(
      `${API_BASE_URL}/fcm-token/`,
      { token },
      {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      }
    );
    console.log('Token FCM sauvegardé:', response.data);
  } catch (error) {
    console.error('Erreur lors de la sauvegarde du token FCM:', error);
    throw error;
  }
};
export const sendFCMNotification = async (
  title: string,
  body: string,
  data?: Record<string, string>
): Promise<{ sent: number; errors: any[] }> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/send-fcm/`, {
      title,
      body,
      data: data || {},
    });
    console.log('Notifications envoyées:', response.data);
    return response.data;
  } catch (error) {
    console.error("Erreur lors de l'envoi de la notification:", error);
    throw error;
  }
};

export const notifyReportGenerated = async (reportDate: string, summary: string) =>
  sendFCMNotification(
    '📊 Nouveau Rapport',
    `Rapport du ${reportDate} généré avec succès`,
    { type: 'daily_report', date: reportDate, action: 'view_report', summary: summary.substring(0, 50) + '...' }
  );

export const notifyForecastAvailable = async (date: string, visitorCount: number) =>
  sendFCMNotification(
    '🔮 Prévision Disponible',
    `Prévision pour ${date}: ${visitorCount} visiteurs estimés`,
    { type: 'forecast', date, visitors: visitorCount.toString(), action: 'view_forecast' }
  );

export const sendAlert = async (alertType: string, message: string) =>
  sendFCMNotification(
    '⚠️ Alerte ShopAnalytics',
    message,
    { type: 'alert', alert_type: alertType, timestamp: new Date().toISOString() }
  );

export default { saveFCMToken, sendFCMNotification, notifyReportGenerated, notifyForecastAvailable, sendAlert };