# `accounts/` — Application Django : authentification

Application Django gérant les comptes utilisateurs (un compte = un commerce), l'authentification par JWT, et la réinitialisation de mot de passe par e-mail (OTP via Gmail SMTP).

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `models.py` | Modèle `User` (auth par e-mail) + `PasswordResetToken` (OTP à usage unique) |
| `managers.py` | `UserManager` — création d'utilisateurs/superutilisateurs par e-mail (pas de `username`) |
| `serializers.py` | Validation des formulaires d'inscription, connexion et réinitialisation de mot de passe |
| `views.py` | Endpoints REST `/api/auth/...` |
| `urls.py` | Routage des endpoints `accounts/` |
| `admin.py` | Interface admin Django pour le modèle `User` |
| `app.py` | Configuration de l'app (`AppConfig`) |
| `0001_initial.py`, `0002_passwordresettoken.py` | Migrations Django |

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
| `POST` | `register/` | `register` | Crée le compte, retourne profil + tokens JWT (access/refresh) |
| `POST` | `login/` | `login` | Authentifie par e-mail + mot de passe, retourne profil + tokens |
| `POST` | `refresh/` | `TokenRefreshView` (simplejwt) | Renouvelle l'access token à partir du refresh token |
| `GET` | `me/` | `me` | Profil de l'utilisateur connecté (`IsAuthenticated`) |
| `POST` | `logout/` | `logout` | Blackliste le refresh token fourni |
| `POST` | `password-reset/request/` | `password_reset_request` | Étape 1 — envoie un OTP par e-mail si le compte existe |
| `POST` | `password-reset/verify/` | `password_reset_verify` | Étape 2 — vérifie le code sans le consommer |
| `POST` | `password-reset/confirm/` | `password_reset_confirm` | Étape 3 — change le mot de passe |

**Sécurité notable :**
- `login` et `password_reset_request` retournent des messages **génériques** (pas de détail champ par champ) pour éviter l'énumération de comptes/e-mails existants.
- Les anciens tokens OTP non utilisés sont invalidés à chaque nouvelle demande de reset (`PasswordResetToken.objects.filter(user=user, used=False).update(used=True)`).

---

## Envoi d'e-mail (`password_reset_request`)

Construit un e-mail HTML + texte brut (template inline dans `views.py`) contenant le code OTP, envoyé via `django.core.mail.EmailMultiAlternatives` en utilisant le backend SMTP configuré dans `config/settings.py` :

```python
EMAIL_BACKEND       = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST          = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER     = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
```

> 🔒 **Confidentialité** — `EMAIL_HOST_USER` (l'adresse Gmail expéditrice) et `EMAIL_HOST_PASSWORD` (un mot de passe d'application Gmail, **pas** le mot de passe du compte) sont des secrets. Ils ne figurent ni dans ce code ni dans `docker-compose.yml` : ils sont injectés au runtime depuis le fichier `.env` à la racine du repo, qui n'est jamais commité (voir `.gitignore` et `.env.example`). Procédure complète dans le `README.md` racine, section 9.

Si l'envoi échoue (mauvaise configuration SMTP, quota Gmail atteint, etc.), l'API retourne une erreur `500` explicite plutôt qu'un faux succès.

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
```
