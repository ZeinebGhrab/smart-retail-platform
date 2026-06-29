// ============================================================
// src/services/auth.ts — Client API pour l'authentification
//
// Stratégie COOKIE HttpOnly :
//   • login / register  → le backend pose les tokens dans des cookies HttpOnly
//   • Le frontend ne stocke PLUS les tokens (ni localStorage, ni sessionStorage)
//   • Seul le profil utilisateur (non-sensible) est gardé en mémoire
//   • isAuthenticated() se base sur la présence du profil en mémoire
//     + un appel /me/ au démarrage pour vérifier la session
// ============================================================

import { API_BASE_URL } from './api';

// ------------------------------------------------------------
// Types
// ------------------------------------------------------------
export interface AuthUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  store_name: string;
  date_joined: string;
}

export interface AuthResponse {
  user: AuthUser;
  // Les tokens ne sont PLUS dans le body — ils voyagent en cookie HttpOnly
}

export interface RegisterPayload {
  firstName: string;
  lastName: string;
  storeName: string;
  email: string;
  password: string;
  confirm: string;
}

export class AuthApiError extends Error {
  status: number;
  fieldErrors: Record<string, string>;

  constructor(message: string, status: number, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = 'AuthApiError';
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

// ------------------------------------------------------------
// Session en mémoire (profil uniquement — pas les tokens)
// Les tokens sont dans les cookies HttpOnly gérés par le navigateur.
// ------------------------------------------------------------
let _currentUser: AuthUser | null = null;

export function setCurrentUser(user: AuthUser | null): void {
  _currentUser = user;
}

export function getStoredUser(): AuthUser | null {
  return _currentUser;
}

/**
 * Vrai si on a un profil utilisateur en mémoire.
 * Au démarrage de l'app, bootstrapAuth() revalide via /me/.
 */
export function isAuthenticated(): boolean {
  return _currentUser !== null;
}

export function clearSession(): void {
  _currentUser = null;
}

// ------------------------------------------------------------
// Bootstrap : appelé une fois au démarrage (App.tsx)
// Vérifie si le cookie de session est encore valide en appelant /me/.
// ------------------------------------------------------------
export async function bootstrapAuth(): Promise<AuthUser | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me/`, {
      credentials: 'include', // envoie les cookies HttpOnly
    });
    if (!res.ok) {
      _currentUser = null;
      return null;
    }
    const user: AuthUser = await res.json();
    _currentUser = user;
    return user;
  } catch {
    _currentUser = null;
    return null;
  }
}

// ------------------------------------------------------------
// Helpers internes
// ------------------------------------------------------------
const FIELD_MAP: Record<string, string> = {
  first_name: 'firstName',
  last_name: 'lastName',
  store_name: 'storeName',
  email: 'email',
  password: 'password',
  confirm: 'confirm',
};

function firstMessage(value: unknown): string {
  if (Array.isArray(value)) return String(value[0] ?? '');
  return String(value ?? '');
}

function parseFieldErrors(body: Record<string, unknown>): Record<string, string> {
  const errors: Record<string, string> = {};
  Object.entries(body).forEach(([key, value]) => {
    if (key === 'detail') return;
    errors[FIELD_MAP[key] || key] = firstMessage(value);
  });
  return errors;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    credentials: 'include',   // <-- envoie ET reçoit les cookies HttpOnly
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  let data: any = {};
  try { data = await res.json(); } catch { /* réponse vide */ }

  if (!res.ok) {
    const fieldErrors = parseFieldErrors(data);
    const message =
      data.detail || Object.values(fieldErrors)[0] || 'Une erreur est survenue.';
    throw new AuthApiError(message, res.status, fieldErrors);
  }

  return data as T;
}

// ------------------------------------------------------------
// Endpoints publics
// ------------------------------------------------------------

/** POST /api/auth/register/ — le backend pose les cookies, on stocke le profil. */
export async function register(fields: RegisterPayload): Promise<AuthUser> {
  const payload = {
    first_name: fields.firstName, last_name: fields.lastName,
    store_name: fields.storeName, email: fields.email,
    password: fields.password, confirm: fields.confirm,
  };
  const data = await postJSON<AuthResponse>('/auth/register/', payload);
  _currentUser = data.user;
  return data.user;
}

/** POST /api/auth/login/ — le backend pose les cookies, on stocke le profil. */
export async function login(
  email: string,
  password: string,
  _remember: boolean = true, // conservé pour compatibilité API — plus utilisé
): Promise<AuthUser> {
  const data = await postJSON<AuthResponse>('/auth/login/', { email, password });
  _currentUser = data.user;
  return data.user;
}

/** POST /api/auth/logout/ — le backend blackliste + supprime les cookies. */
export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    // On nettoie quand même la session locale
  }
  _currentUser = null;
}

/** GET /api/auth/me/ — profil de l'utilisateur connecté. */
export async function getMe(): Promise<AuthUser> {
  const res = await fetch(`${API_BASE_URL}/auth/me/`, {
    credentials: 'include',
  });
  if (!res.ok) {
    _currentUser = null;
    throw new AuthApiError('Session expirée, merci de vous reconnecter.', res.status);
  }
  const user: AuthUser = await res.json();
  _currentUser = user;
  return user;
}

// ── Mot de passe oublié ──────────────────────────────────────

export async function requestPasswordReset(email: string): Promise<{ detail: string }> {
  return postJSON('/auth/password-reset/request/', { email });
}

export async function verifyResetCode(email: string, code: string): Promise<{ detail: string }> {
  return postJSON('/auth/password-reset/verify/', { email, code });
}

export async function confirmPasswordReset(
  email: string, code: string, password: string, confirm: string,
): Promise<{ detail: string }> {
  return postJSON('/auth/password-reset/confirm/', { email, code, password, confirm });
}

// ── Compat : ces exports n'ont plus de sens mais sont gardés pour
//    éviter des erreurs de compile dans du code non encore mis à jour.
export const getAccessToken  = (): null => null;
export const getRefreshToken = (): null => null;
export const saveSession     = (): void => {};