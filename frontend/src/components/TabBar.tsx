import React from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import './TabBar.css';

// FIX: la TabBar ne référence plus que les routes réellement déclarées
// dans App.tsx (Dashboard, Chat IA, Prédictions). Les anciens onglets
// (Caméras, Reco IA, Planning, Perf., Affectation, Magasins) menaient
// vers des pages inexistantes — supprimés pour éviter les écrans blancs.
const TABS = [
  { label: 'Dashboard',   path: '/dashboard',   icon: 'ti-layout-dashboard' },
  { label: 'Chat IA',     path: '/chat',        icon: 'ti-message-chatbot'  },
  { label: 'Prédictions', path: '/predictions', icon: 'ti-chart-histogram' },
];

const TabBar: React.FC = () => {
  const history  = useHistory();
  const location = useLocation();

  // Pas de barre d'onglets sur les écrans d'authentification.
  if (location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  const go = (path: string) => history.push(path);
  const active = (path: string) => location.pathname === path;

  return (
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
      </div>
    </nav>
  );
};

export default TabBar;