import React from 'react';
import { IonTabBar, IonTabButton, IonLabel } from '@ionic/react';
import { useHistory, useLocation } from 'react-router-dom';
import './TabBar.css';

const TABS_ROW1 = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Caméras',   path: '/cameras'   },
  { label: 'Reco IA',   path: '/reco'      },
  { label: 'Chat IA',   path: '/chat'      },
  { label: 'Planning',  path: '/planning'  },
  { label: 'Perf.',     path: '/perf'      },
];

const TABS_ROW2 = [
  { label: 'Affectation', path: '/affectation' },
  { label: 'Magasins',    path: '/magasins'    },
  { label: 'Prédictions', path: '/predictions' },
];

const TabBar: React.FC = () => {
  const history  = useHistory();
  const location = useLocation();

  const go = (path: string) => history.push(path);
  const active = (path: string) => location.pathname === path;

  return (
    <div className="tab-bar-wrapper">
      {/* Row 1 */}
      <div className="tab-row">
        {TABS_ROW1.map((t) => (
          <button
            key={t.path}
            className={`tab-btn ${active(t.path) ? 'active' : ''}`}
            onClick={() => go(t.path)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {/* Row 2 */}
      <div className="tab-row">
        {TABS_ROW2.map((t) => (
          <button
            key={t.path}
            className={`tab-btn ${active(t.path) ? 'active' : ''}`}
            onClick={() => go(t.path)}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default TabBar;
