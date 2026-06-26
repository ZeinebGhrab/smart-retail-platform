import React from 'react';
import { IonApp, IonRouterOutlet, setupIonicReact } from '@ionic/react';
import { IonReactRouter } from '@ionic/react-router';
import { Route, Redirect } from 'react-router-dom';

import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';

import ChatIA from '../features/chat/ChatIA';
import Historique from '../features/historique/Historique';
import TabBar from '../components/TabBar';
import Dashboard from '../features/dashboard/Dashboard';
import Login from '../features/auth/Login';
import Register from '../features/auth/Register';
import PrivateRoute from '../components/PrivateRoute';
import { isAuthenticated } from '../services/auth';
import { useFirebaseMessaging } from '../hooks/useFirebaseMessaging';
import Alerts from '../features/alerts/Alerts';
import AlertDetail from '../features/alerts/AlertDetail';

setupIonicReact();

const App: React.FC = () => {
  // Enregistre le token FCM (natif sur Android, best effort sur web)
  // une seule fois au démarrage de l'app.
  useFirebaseMessaging();

  return (
    <IonApp>
      <IonReactRouter>
        <IonRouterOutlet>
          {/* ── Authentification (publiques) ───────────────── */}
          <Route exact path="/login"    component={Login}    />
          <Route exact path="/register" component={Register} />

          {/* ── Application (protégées par token JWT) ──────── */}
          <PrivateRoute exact path="/dashboard"   component={Dashboard}  />
          <PrivateRoute exact path="/chat"        component={ChatIA}     />
          <PrivateRoute exact path="/predictions" component={Historique} />
          <PrivateRoute exact path="/alerts" component={Alerts} />
          <PrivateRoute exact path="/alerts/:id" component={AlertDetail} />
          {/* Connecté → dashboard, sinon → login */}
          <Redirect exact from="/" to={isAuthenticated() ? '/dashboard' : '/login'} />
        </IonRouterOutlet>
        <TabBar />
      </IonReactRouter>
    </IonApp>
  );
};

export default App;