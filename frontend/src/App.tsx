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
import TabBar from './components/TabBar';

setupIonicReact();

const App: React.FC = () => (
  <IonApp>
    <IonReactRouter>
      {/* Main outlet takes up the space above the tab bar */}
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          <IonRouterOutlet>
            <Route exact path="/chat" component={ChatIA} />
            {/* Add other routes here as you build them */}
            <Redirect exact from="/" to="/chat" />
          </IonRouterOutlet>
        </div>
        <TabBar />
      </div>
    </IonReactRouter>
  </IonApp>
);

export default App;
