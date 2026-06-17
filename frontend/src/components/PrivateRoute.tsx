// ============================================================
// src/components/PrivateRoute.tsx — Garde d'accès aux routes protégées
// Redirige vers /login si aucun token d'accès n'est présent localement.
// ============================================================

import React from 'react';
import { Redirect, Route, RouteProps } from 'react-router-dom';
import { isAuthenticated } from '../services/auth';

const PrivateRoute: React.FC<RouteProps> = ({ component: Component, ...rest }) => {
  if (!Component) return null;

  return (
    <Route
      {...rest}
      render={(props) =>
        isAuthenticated() ? (
          <Component {...props} />
        ) : (
          <Redirect to={{ pathname: '/login', state: { from: props.location } }} />
        )
      }
    />
  );
};

export default PrivateRoute;