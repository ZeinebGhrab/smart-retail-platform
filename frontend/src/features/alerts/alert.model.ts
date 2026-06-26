// Modèle de données aligné sur le contenu envoyé par le bot Telegram
// (ex: "Attention : Geste suspect de vol (100%)" + "#Cam_23_MG_Ennasser_20260609-202622223137")

export type AlertStatus =
  | 'en_attente'                      // pas encore qualifiée
  | 'vol_confirme_interpelle'         // bouton Telegram "Vol confirmé (client interpellé)"
  | 'vol_confirme_non_interpelle'     // bouton Telegram "Vol confirmé (client non interpellé)"
  | 'comportement_suspect'            // bouton Telegram "Comportement suspect"
  | 'fausse_alerte';                  // bouton Telegram "Fausse alerte"

export interface SecurityAlert {
  id: string;
  cameraId: string;        // ex: "Cam_23"
  cameraLabel: string;      // ex: "Caméra 23"
  location: string;         // ex: "MG Ennasser"
  rawTag: string;           // ex: "#Cam_23_MG_Ennasser_20260609-202622223137" (référence brute envoyée par le bot)
  message: string;          // ex: "Geste suspect de vol"
  confidence: number;       // 0-100
  videoUrl?: string;
  thumbnailUrl?: string;
  createdAt: string;        // ISO datetime
  status: AlertStatus;
  qualifiedBy?: string;     // ex: "@khalilaraar" — qui a qualifié l'alerte (sur Telegram ou dans l'app)
  qualifiedAt?: string;
}

export const ALERT_STATUS_LABELS: Record<AlertStatus, string> = {
  en_attente: 'En attente',
  vol_confirme_interpelle: 'Vol confirmé (interpellé)',
  vol_confirme_non_interpelle: 'Vol confirmé (non interpellé)',
  comportement_suspect: 'Comportement suspect',
  fausse_alerte: 'Fausse alerte',
};
