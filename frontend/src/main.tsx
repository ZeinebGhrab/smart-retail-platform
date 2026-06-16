import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// FIX #3 : importer les variables de thème Ionic AVANT App
// (était absent → IonPage gardait le fond blanc par défaut)
import './theme/variables.css';

const container = document.getElementById('root');
const root = createRoot(container!);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);