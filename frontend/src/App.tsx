import React from 'react';
import { IonApp, IonRouterOutlet, setupIonicReact } from '@ionic/react';
import { IonReactRouter } from '@ionic/react-router';
import { Route, Redirect } from 'react-router-dom';

import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';

import ChatIA from './pages/ChatIA';
import Historique from './pages/Historique';
import TabBar from './components/TabBar';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Register from './pages/Register';
import PrivateRoute from './components/PrivateRoute';
import { isAuthenticated } from './services/auth';

setupIonicReact();

const App: React.FC = () => (
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

        {/* Connecté → dashboard, sinon → login */}
        <Redirect exact from="/" to={isAuthenticated() ? '/dashboard' : '/login'} />
      </IonRouterOutlet>
      <TabBar />
    </IonReactRouter>
  </IonApp>
);

export default App;