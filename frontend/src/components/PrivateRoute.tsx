// ============================================================
// src/components/PrivateRoute.tsx
// Garde d'accès aux routes protégées.
//   • Redirige vers /login si aucune session n'est présente.
//   • Écoute l'événement global "auth:expired" émis par authAxios
//     pour forcer la redirection dès qu'un 401 non récupérable survient.
//
// CORRECTIF : l'ancienne version initialisait [authed] avec useState une
// seule fois au montage. Si bootstrapAuth() finissait après le premier
// render, authed restait false et redirigait vers /login même avec un
// cookie valide. On lit maintenant isAuthenticated() directement à chaque
// render via un compteur de force-refresh (tick).
// ============================================================

import React, { useEffect, useState } from 'react';
import { Redirect, Route, RouteProps, useHistory } from 'react-router-dom';
import { isAuthenticated } from '../services/auth';

const PrivateRoute: React.FC<RouteProps> = ({
  component: Component,
  ...rest
}) => {
  const history = useHistory();

  // CORRECTIF : on n'utilise plus useState(isAuthenticated()) comme valeur initiale figée.
  // On force un re-render via un compteur (tick) quand l'état auth change,
  // et on relit isAuthenticated() à chaque render pour avoir la valeur fraîche.
  const [tick, setTick] = useState(0);
  const authed = isAuthenticated();

  // Écoute l'événement "auth:expired" déclenché par authAxios
  // quand le refresh token est lui aussi invalide.
  useEffect(() => {
    const handleExpired = () => {
      setTick((t) => t + 1); // force re-render pour relire isAuthenticated()
      history.replace('/login');
    };

    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, [history]);

  // Écoute l'événement "auth:ready" émis par App.tsx après bootstrapAuth()
  // pour se re-rendre une fois la session confirmée.
  useEffect(() => {
    const handleReady = () => setTick((t) => t + 1);
    window.addEventListener('auth:ready', handleReady);
    return () => window.removeEventListener('auth:ready', handleReady);
  }, []);

  if (!Component) return null;

  return (
    <Route
      {...rest}
      render={(props) =>
        authed ? (
          <Component {...props} />
        ) : (
          <Redirect
            to={{ pathname: '/login', state: { from: props.location } }}
          />
        )
      }
    />
  );
};

export default PrivateRoute;