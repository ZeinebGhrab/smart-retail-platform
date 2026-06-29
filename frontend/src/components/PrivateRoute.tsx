// ============================================================
// src/components/PrivateRoute.tsx
// Garde d'accès aux routes protégées.
//   • Redirige vers /login si aucun token n'est présent.
//   • Écoute l'événement global "auth:expired" émis par authAxios
//     pour forcer la redirection dès qu'un 401 non récupérable survient.
// ============================================================

import React, { useEffect, useState } from 'react';
import { Redirect, Route, RouteProps, useHistory } from 'react-router-dom';
import { isAuthenticated } from '../services/auth';

const PrivateRoute: React.FC<RouteProps> = ({
  component: Component,
  ...rest
}) => {
  const history = useHistory();
  const [authed, setAuthed] = useState<boolean>(isAuthenticated());

  // Écoute l'événement "auth:expired" déclenché par authAxios
  // quand le refresh token est lui aussi invalide.
  useEffect(() => {
    const handleExpired = () => {
      setAuthed(false);
      history.replace('/login');
    };

    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, [history]);

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