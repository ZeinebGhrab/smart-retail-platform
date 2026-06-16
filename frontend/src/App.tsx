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

setupIonicReact();

const App: React.FC = () => (
  <IonApp>
    <IonReactRouter>
      <IonRouterOutlet>
        <Route exact path="/dashboard"   component={Dashboard}  />
        <Route exact path="/chat"        component={ChatIA}     />
        <Route exact path="/predictions" component={Historique} />
        <Redirect exact from="/" to="/dashboard" />
      </IonRouterOutlet>
      <TabBar />
    </IonReactRouter>
  </IonApp>
);

export default App;