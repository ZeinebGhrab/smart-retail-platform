// ============================================================
// frontend/src/services/fcm.ts
// Service pour interagir avec les endpoints FCM du backend
// ============================================================

// ce fichier utilisait axios brut + getAccessToken() (qui
// renvoie toujours null depuis le passage à l'auth par cookie HttpOnly).
// Sans withCredentials: true, le cookie de session n'était jamais
// envoyé → /fcm-token/ et /send-fcm/ étaient appelés sans authentification.
// authAxios (withCredentials: true + refresh auto sur 401) est la bonne
// instance à utiliser ici, comme partout ailleurs dans l'app.
import authAxios from './authAxios';

export const saveFCMToken = async (token: string): Promise<void> => {
  try {
    const response = await authAxios.post('/fcm-token/', { token });
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
    const response = await authAxios.post('/send-fcm/', {
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