import React from 'react';
import { IonApp, IonRouterOutlet, setupIonicReact } from '@ionic/react';
import { IonReactRouter } from '@ionic/react-router';
import { Route, Redirect } from 'react-router-dom';

/* Core Ionic CSS */
import '@ionic/react/css/core.css';
import '@ionic/react/css/normalize.css';
import '@ionic/react/css/structure.css';
import '@ionic/react/css/typography.css';

/* Pages */
import ChatIA from './pages/ChatIA';
import Historique from './pages/Historique';
import TabBar from './components/TabBar';
import Dashboard from './pages/Dashboard';

setupIonicReact();

const App: React.FC = () => (
  <IonApp>
    <IonReactRouter>
      {/* Main outlet takes up the space above the tab bar */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          <IonRouterOutlet>
            <Route exact path="/dashboard"   component={Dashboard}  />
            <Route exact path="/chat"        component={ChatIA}     />
            <Route exact path="/predictions" component={Historique} />
            {/* FIX #1 : rediriger vers /dashboard au démarrage, pas /chat */}
            <Redirect exact from="/" to="/dashboard" />
          </IonRouterOutlet>
        </div>
        <TabBar />
      </div>
    </IonReactRouter>
  </IonApp>
);

export default App;