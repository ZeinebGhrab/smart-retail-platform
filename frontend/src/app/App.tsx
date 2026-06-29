// ============================================================
// src/app/App.tsx
// Ajout du bootstrapAuth() au démarrage :
//   • Appelle GET /api/auth/me/ avec credentials: 'include'
//   • Si le cookie est encore valide → utilisateur reconnecté silencieusement
//   • Sinon → isAuthenticated() = false → redirect /login par PrivateRoute
// ============================================================

import React, { useEffect, useState } from 'react';
import { IonApp, IonRouterOutlet, IonSpinner, setupIonicReact } from '@ionic/react';
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
import Alerts from '../features/alerts/Alerts';
import AlertDetail from '../features/alerts/AlertDetail';
import { bootstrapAuth, isAuthenticated } from '../services/auth';
import { useFirebaseMessaging } from '../hooks/useFirebaseMessaging';

setupIonicReact();

const App: React.FC = () => {
  useFirebaseMessaging();

  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Vérifie silencieusement si le cookie de session est encore valide.
    // Tant qu'on attend, on affiche un spinner pour éviter un flash de /login.
    bootstrapAuth().finally(() => setReady(true));
  }, []);

  if (!ready) {
    return (
      <IonApp>
        <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
          <IonSpinner name="crescent" />
        </div>
      </IonApp>
    );
  }

  return (
    <IonApp>
      <IonReactRouter>
        <IonRouterOutlet>
          {/* ── Publiques ───────────────────────────────────── */}
          <Route exact path="/login"    component={Login}    />
          <Route exact path="/register" component={Register} />

          {/* ── Protégées par session cookie ────────────────── */}
          <PrivateRoute exact path="/dashboard"   component={Dashboard}  />
          <PrivateRoute exact path="/chat"        component={ChatIA}     />
          <PrivateRoute exact path="/predictions" component={Historique} />
          <PrivateRoute exact path="/alerts"      component={Alerts}     />
          <PrivateRoute exact path="/alerts/:id"  component={AlertDetail} />

          <Redirect exact from="/" to={isAuthenticated() ? '/dashboard' : '/login'} />
        </IonRouterOutlet>
        <TabBar />
      </IonReactRouter>
    </IonApp>
  );
};

export default App;