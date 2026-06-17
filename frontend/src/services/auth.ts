// ============================================================
// src/services/auth.ts — Client API pour l'authentification
// (inscription / connexion / session) — backend Django (accounts/)
//
// Endpoints consommés :
//   POST /api/auth/register/  ← Register.tsx
//   POST /api/auth/login/     ← Login.tsx
//   POST /api/auth/logout/
//   GET  /api/auth/me/
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

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthResponse extends AuthTokens {
  user: AuthUser;
}

/** Champs du formulaire Register.tsx (camelCase côté front). */
export interface RegisterPayload {
  firstName: string;
  lastName: string;
  storeName: string;
  email: string;
  password: string;
  confirm: string;
}

/**
 * Erreur renvoyée par l'API auth. `fieldErrors` est déjà converti en clés
 * camelCase (firstName, lastName, storeName, email, password, confirm)
 * pour être branché directement sur le state `errors` des formulaires.
 */
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
// Session locale (tokens JWT + profil utilisateur)
// "remember" (Login.tsx) → localStorage (persiste après fermeture du
// navigateur) sinon sessionStorage (effacé à la fermeture de l'onglet).
// ------------------------------------------------------------
const ACCESS_KEY = 'anavid_access_token';
const REFRESH_KEY = 'anavid_refresh_token';
const USER_KEY = 'anavid_user';

function clearStorage(storage: Storage): void {
  storage.removeItem(ACCESS_KEY);
  storage.removeItem(REFRESH_KEY);
  storage.removeItem(USER_KEY);
}

export function saveSession(data: AuthResponse, remember: boolean = true): void {
  // On nettoie les deux storages avant d'écrire pour éviter un état
  // incohérent si l'utilisateur change d'avis entre deux connexions.
  clearStorage(localStorage);
  clearStorage(sessionStorage);

  const storage = remember ? localStorage : sessionStorage;
  storage.setItem(ACCESS_KEY, data.access);
  storage.setItem(REFRESH_KEY, data.refresh);
  storage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function clearSession(): void {
  clearStorage(localStorage);
  clearStorage(sessionStorage);
}

function readEither(key: string): string | null {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

export function getAccessToken(): string | null {
  return readEither(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return readEither(REFRESH_KEY);
}

export function getStoredUser(): AuthUser | null {
  const raw = readEither(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

/** Vrai si un access token est présent localement (présence uniquement, pas de vérif d'expiration). */
export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

// ------------------------------------------------------------
// Mapping des erreurs de validation (snake_case backend → camelCase front)
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
    if (key === 'detail') return; // message global, pas un champ
    errors[FIELD_MAP[key] || key] = firstMessage(value);
  });
  return errors;
}

async function postJSON<T>(path: string, body: unknown, accessToken?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  let data: any = {};
  try {
    data = await res.json();
  } catch {
    // Réponse vide (ex: certaines erreurs serveur) — on garde data = {}
  }

  if (!res.ok) {
    const fieldErrors = parseFieldErrors(data);
    const message =
      data.detail ||
      Object.values(fieldErrors)[0] ||
      'Une erreur est survenue. Réessayez.';
    throw new AuthApiError(message, res.status, fieldErrors);
  }

  return data as T;
}

// ------------------------------------------------------------
// Endpoints
// ------------------------------------------------------------

/**
 * POST /api/auth/register/ — création de compte (Register.tsx).
 * Stocke la session (déjà connecté) au succès.
 */
export async function register(fields: RegisterPayload): Promise<AuthResponse> {
  const payload = {
    first_name: fields.firstName,
    last_name: fields.lastName,
    store_name: fields.storeName,
    email: fields.email,
    password: fields.password,
    confirm: fields.confirm,
  };
  const data = await postJSON<AuthResponse>('/auth/register/', payload);
  saveSession(data, true);
  return data;
}

/**
 * POST /api/auth/login/ — connexion (Login.tsx).
 * `remember` détermine si la session survit à la fermeture du navigateur.
 */
export async function login(email: string, password: string, remember: boolean = true): Promise<AuthResponse> {
  const data = await postJSON<AuthResponse>('/auth/login/', { email, password });
  saveSession(data, remember);
  return data;
}

/** POST /api/auth/logout/ — invalide le refresh token côté serveur puis nettoie la session locale. */
export async function logout(): Promise<void> {
  const refresh = getRefreshToken();
  const access = getAccessToken();
  if (refresh && access) {
    try {
      await postJSON('/auth/logout/', { refresh }, access);
    } catch {
      // On nettoie quand même la session locale (token déjà expiré, réseau coupé, etc.)
    }
  }
  clearSession();
}

/** GET /api/auth/me/ — profil de l'utilisateur connecté (vérifie/rafraîchit le profil en cache). */
export async function getMe(): Promise<AuthUser> {
  const access = getAccessToken();
  const res = await fetch(`${API_BASE_URL}/auth/me/`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  if (!res.ok) {
    throw new AuthApiError('Session expirée, merci de vous reconnecter.', res.status);
  }
  return res.json() as Promise<AuthUser>;
}