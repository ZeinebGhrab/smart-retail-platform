# `accounts/` — Application Django : authentification

Application Django gérant les comptes utilisateurs (un compte = un commerce), l'authentification par JWT via **cookie HttpOnly**, et la réinitialisation de mot de passe par e-mail (OTP via Gmail SMTP).

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `models.py` | Modèle `User` (auth par e-mail) + `PasswordResetToken` (OTP à usage unique) |
| `managers.py` | `UserManager` — création d'utilisateurs/superutilisateurs par e-mail (pas de `username`) |
| `serializers.py` | Validation des formulaires d'inscription, connexion et réinitialisation de mot de passe |
| `views.py` | Endpoints REST `/api/auth/...` — pose et supprime les cookies JWT |
| `authentication.py` | `CookieJWTAuthentication` — lit le JWT depuis le header `Authorization` ou le cookie HttpOnly |
| `urls.py` | Routage des endpoints `accounts/` |
| `admin.py` | Interface admin Django pour le modèle `User` |
| `app.py` | Configuration de l'app (`AppConfig`) |
| `0001_initial.py`, `0002_passwordresettoken.py` | Migrations Django |

---

## Stratégie d'authentification : cookie HttpOnly

Les tokens JWT ne transitent **plus** dans le corps des réponses JSON. À la place, le backend les pose dans des **cookies HttpOnly** au moment du login ou de l'inscription, et les lit automatiquement sur les requêtes suivantes.

| Cookie | Contenu | Durée |
|---|---|---|
| `anavid_access` | Access token JWT | 60 minutes |
| `anavid_refresh` | Refresh token JWT | 14 jours |

Paramètres configurables dans `config/settings.py` :

```python
JWT_AUTH_COOKIE           = "anavid_access"
JWT_AUTH_REFRESH_COOKIE   = "anavid_refresh"
JWT_AUTH_COOKIE_SECURE    = False   # True en production (HTTPS)
JWT_AUTH_COOKIE_SAMESITE  = "Lax"
JWT_AUTH_COOKIE_HTTP_ONLY = True
```

---

## `authentication.py` — `CookieJWTAuthentication`

Sous-classe de `JWTAuthentication` (simplejwt) isolée dans son propre fichier pour éviter l'import circulaire avec DRF (qui charge `DEFAULT_AUTHENTICATION_CLASSES` très tôt au démarrage, avant que `rest_framework.views` soit initialisé).

Logique en deux étapes :

1. **Header `Authorization: Bearer <token>`** — comportement standard simplejwt, compatible Swagger et Postman.
2. **Cookie `anavid_access`** — fallback si le header est absent. Le token brut est validé directement.

> **Correctif sprint 2** — L'ancienne implémentation passait `f"Bearer {raw_token}".encode()` à `get_raw_token()`, qui attend un token **brut** (sans préfixe). Cela provoquait un échec de validation systématique sur toutes les requêtes passant par cookie, renvoyant un 401 même avec un cookie valide.
>
> ```python
> # AVANT (bug) — préfixe "Bearer " passé à get_raw_token() qui l'attend sans préfixe
> validated = self.get_validated_token(self.get_raw_token(f"Bearer {raw_token}".encode()))
>
> # APRÈS (correct) — token brut directement
> validated = self.get_validated_token(raw_token.encode())
> ```

---

## Modèle de données (`models.py`)

### `User`

Hérite d'`AbstractUser` avec `username` désactivé : l'**e-mail** est l'identifiant unique de connexion (`USERNAME_FIELD = "email"`). Champs alignés sur le formulaire `Register.tsx` du frontend :

| Champ | Description |
|---|---|
| `email` | Identifiant unique, utilisé pour la connexion |
| `first_name`, `last_name` | Hérités d'`AbstractUser` |
| `store_name` | Nom du commerce — un compte représente un commerce |

### `PasswordResetToken`

Code OTP à 6 chiffres (`_otp_code()`), lié à un `User` :

| Champ / méthode | Rôle |
|---|---|
| `code` | Code à 6 chiffres généré aléatoirement |
| `created_at` | Horodatage de création |
| `used` | Passe à `True` après consommation |
| `OTP_LIFETIME` | 15 minutes |
| `is_valid()` | `True` si non utilisé et non expiré |
| `consume()` | Marque le token comme utilisé |

---

## Endpoints (`views.py` / `urls.py`)

Base : `http://localhost:8000/api/auth/`

| Méthode | URL | Vue | Description |
|---|---|---|---|
| `POST` | `register/` | `register` | Crée le compte, pose les cookies `anavid_access` + `anavid_refresh`, retourne le profil |
| `POST` | `login/` | `login` | Authentifie par e-mail + mot de passe, pose les cookies, retourne le profil |
| `POST` | `refresh/` | `token_refresh` | Lit le cookie `anavid_refresh`, pose un nouveau cookie `anavid_access` |
| `GET` | `me/` | `me` | Profil de l'utilisateur connecté — authentifié via `CookieJWTAuthentication` |
| `POST` | `logout/` | `logout` | Blackliste le refresh token + supprime les deux cookies |
| `POST` | `password-reset/request/` | `password_reset_request` | Étape 1 — envoie un OTP par e-mail si le compte existe |
| `POST` | `password-reset/verify/` | `password_reset_verify` | Étape 2 — vérifie le code sans le consommer |
| `POST` | `password-reset/confirm/` | `password_reset_confirm` | Étape 3 — change le mot de passe |

**Sécurité notable :**
- `login` et `password_reset_request` retournent des messages **génériques** pour éviter l'énumération de comptes.
- Les anciens tokens OTP non utilisés sont invalidés à chaque nouvelle demande de reset.
- Les cookies sont posés avec `HttpOnly: True` — JavaScript ne peut pas les lire (protection XSS).
- `SameSite: Lax` + `Secure: False` en développement ; passer `JWT_COOKIE_SECURE=true` en production.

---

## Envoi d'e-mail (`password_reset_request`)

Construit un e-mail texte brut contenant le code OTP, envoyé via `EmailMultiAlternatives` en utilisant le backend SMTP configuré dans `config/settings.py` :

```python
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
```

> 🔒 **Confidentialité** — `EMAIL_HOST_USER` et `EMAIL_HOST_PASSWORD` sont des secrets injectés depuis `.env` au runtime (jamais commités). Procédure complète dans le `README.md` racine, section 9.

Si l'envoi échoue, l'API retourne une erreur `500` explicite plutôt qu'un faux succès.

---

## Exemple d'utilisation (Swagger : `/api/docs/`)

```json
// POST /api/auth/register/
{
  "first_name": "Ali",
  "last_name": "Ben Salem",
  "store_name": "Boutique El Amal",
  "email": "ali@example.com",
  "password": "motdepasse123",
  "confirm": "motdepasse123"
}
```

```json
// POST /api/auth/login/
{ "email": "ali@example.com", "password": "motdepasse123" }
// → réponse : { "user": { ... } }
// → cookies posés : anavid_access, anavid_refresh (HttpOnly)
```

> Pour tester les endpoints protégés dans Swagger, cliquez sur **Authorize** et entrez `Bearer <votre_token>` (obtenu via `/login/` dans le corps de la réponse en mode debug, ou en lisant le cookie via les DevTools).