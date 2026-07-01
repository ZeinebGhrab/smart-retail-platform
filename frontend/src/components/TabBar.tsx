import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useIonRouter } from '@ionic/react';
import { logout } from '../services/auth';
import './TabBar.css';

const TABS = [
  { label: 'Dashboard', path: '/dashboard', icon: 'ti-layout-dashboard' },
  { label: 'Chat IA', path: '/chat', icon: 'ti-message-chatbot' },
  { label: 'Prédictions', path: '/predictions', icon: 'ti-chart-histogram' },
];

const TabBar: React.FC = () => {
  const ionRouter = useIonRouter();
  const location = useLocation();
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  // Pas de barre d'onglets sur les écrans d'authentification.
  if (location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  const go = (path: string) => ionRouter.push(path);
  const active = (path: string) => location.pathname === path;
  const handleLogout = async () => {
    setLoading(true);
    try {
      await logout();
    } finally {
      // window.location.replace évite le cycle infini que provoque
      // history.push('/login') quand PrivateRoute tente simultanément
      // de rediriger (Maximum update depth exceeded avec Ionic Router).
      window.location.replace('/login');
    }
  };

  return (
    <>
      {/* Modal de confirmation */}
      {showConfirm && (
        <div className="logout-overlay" onClick={() => setShowConfirm(false)}>
          <div className="logout-modal" onClick={(e) => e.stopPropagation()}>
            <div className="logout-modal-icon">
              <span className="ti ti-logout" />
            </div>
            <h3 className="logout-modal-title">Déconnexion</h3>
            <p className="logout-modal-text">Voulez-vous vraiment vous déconnecter&nbsp;?</p>
            <div className="logout-modal-actions">
              <button
                className="logout-modal-btn cancel"
                onClick={() => setShowConfirm(false)}
                disabled={loading}
              >
                Annuler
              </button>
              <button
                className="logout-modal-btn confirm"
                onClick={handleLogout}
                disabled={loading}
              >
                {loading ? (
                  <span className="logout-spinner" />
                ) : (
                  'Se déconnecter'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      <nav className="tab-bar-wrapper" aria-label="Navigation principale">
        <div className="tab-row">
          {TABS.map((t) => (
            <button
              key={t.path}
              className={`tab-btn ${active(t.path) ? 'active' : ''}`}
              onClick={() => go(t.path)}
              aria-current={active(t.path) ? 'page' : undefined}
            >
              <span className={`ti ${t.icon} tab-btn-icon`} aria-hidden="true" />
              <span className="tab-btn-label">{t.label}</span>
            </button>
          ))}

          {/* Bouton Logout */}
          <button
            className="tab-btn tab-btn-logout"
            onClick={() => setShowConfirm(true)}
            aria-label="Se déconnecter"
          >
            <span className="ti ti-logout tab-btn-icon" aria-hidden="true" />
            <span className="tab-btn-label">Quitter</span>
          </button>
        </div>
      </nav>
    </>
  );
};

export default TabBar;