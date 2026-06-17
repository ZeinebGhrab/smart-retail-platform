// ============================================================
// frontend/src/services/fcm.ts
// Service pour interagir avec les endpoints FCM du backend
// ============================================================

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

/**
 * Sauvegarde le token FCM sur le serveur
 */
export const saveFCMToken = async (token: string): Promise<void> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/fcm-token/`, {
      token
    });
    console.log('Token FCM sauvegardé:', response.data);
  } catch (error) {
    console.error('Erreur lors de la sauvegarde du token FCM:', error);
    throw error;
  }
};

/**
 * Envoie une notification FCM à tous les appareils enregistrés
 * (À utiliser depuis l'admin ou un dashboard)
 */
export const sendFCMNotification = async (
  title: string,
  body: string,
  data?: Record<string, string>
): Promise<{ sent: number; errors: any[] }> => {
  try {
    const response = await axios.post(`${API_BASE_URL}/send-fcm/`, {
      title,
      body,
      data: data || {}
    });
    console.log('Notifications envoyées:', response.data);
    return response.data;
  } catch (error) {
    console.error('Erreur lors de l\'envoi de la notification:', error);
    throw error;
  }
};

/**
 * Exemple d'intégration avec le ChatIA
 * Envoyer une notification quand un rapport est généré
 */
export const notifyReportGenerated = async (reportDate: string, summary: string) => {
  return sendFCMNotification(
    '📊 Nouveau Rapport',
    `Rapport du ${reportDate} généré avec succès`,
    {
      type: 'daily_report',
      date: reportDate,
      action: 'view_report',
      summary: summary.substring(0, 50) + '...'
    }
  );
};

/**
 * Exemple d'intégration avec les prévisions
 * Envoyer une notification quand une prévision est disponible
 */
export const notifyForecastAvailable = async (date: string, visitorCount: number) => {
  return sendFCMNotification(
    '🔮 Prévision Disponible',
    `Prévision pour ${date}: ${visitorCount} visiteurs estimés`,
    {
      type: 'forecast',
      date: date,
      visitors: visitorCount.toString(),
      action: 'view_forecast'
    }
  );
};

/**
 * Exemple d'intégration avec les alertes
 * Envoyer une notification d'alerte
 */
export const sendAlert = async (alertType: string, message: string) => {
  return sendFCMNotification(
    '⚠️ Alerte ShopAnalytics',
    message,
    {
      type: 'alert',
      alert_type: alertType,
      timestamp: new Date().toISOString()
    }
  );
};

export default {
  saveFCMToken,
  sendFCMNotification,
  notifyReportGenerated,
  notifyForecastAvailable,
  sendAlert
};