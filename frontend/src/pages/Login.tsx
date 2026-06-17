import React, { useState } from 'react';
import { IonPage, IonContent } from '@ionic/react';
import { useHistory } from 'react-router-dom';
import './Auth.css';

// ─── Inline SVG icons (no extra dep) ────────────────────────
const IconStore = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const IconMail = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="2"/>
    <path d="m22 7-8.97 5.7a1.94 1.94 0 01-2.06 0L2 7"/>
  </svg>
);

const IconLock = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0110 0v4"/>
  </svg>
);

const IconEye = ({ off }: { off?: boolean }) => off ? (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
    <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
) : (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);

const IconAlert = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="12"/>
    <line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);

// ─── Validation helpers ──────────────────────────────────────
const validateEmail = (v: string) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? '' : 'Adresse e-mail invalide';

const validatePassword = (v: string) =>
  v.length < 6 ? 'Le mot de passe doit contenir au moins 6 caractères' : '';

// ─── Component ───────────────────────────────────────────────
const Login: React.FC = () => {
  const history = useHistory();

  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [showPw, setShowPw]       = useState(false);
  const [remember, setRemember]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [globalErr, setGlobalErr] = useState('');

  const [errors, setErrors] = useState<{ email: string; password: string }>({
    email: '', password: '',
  });

  const validate = () => {
    const e = { email: validateEmail(email), password: validatePassword(password) };
    setErrors(e);
    return !e.email && !e.password;
  };

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setGlobalErr('');
    if (!validate()) return;

    setLoading(true);
    try {
      // TODO: remplacer par un vrai appel API
      await new Promise(r => setTimeout(r, 1200));

      // Simulation : si email = test@test.com → succès
      if (email === 'test@test.com' && password === 'password') {
        history.replace('/dashboard');
      } else {
        setGlobalErr('Identifiants incorrects. Vérifiez votre e-mail et mot de passe.');
      }
    } catch {
      setGlobalErr('Connexion impossible. Réessayez dans un moment.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <IonPage className="auth-page">
      <IonContent className="auth-scroll" scrollY>
        <div className="auth-content">

          {/* Brand */}
          <div className="auth-brand">
            <div className="auth-logo-ring">
              <IconStore />
            </div>
            <span className="auth-brand-name">Anavid</span>
            <span className="auth-brand-tag">Smart Retail Platform</span>
          </div>

          {/* Card */}
          <div className="auth-card">
            <h1 className="auth-card-title">Connexion</h1>
            <p className="auth-card-subtitle">Bienvenue ! Accédez à votre tableau de bord.</p>

            {globalErr && (
              <div className="auth-alert" style={{ marginBottom: 16 }}>
                <IconAlert /> {globalErr}
              </div>
            )}

            <form className="auth-form" onSubmit={handleSubmit} noValidate>

              {/* Email */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="login-email">Adresse e-mail</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconMail /></span>
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    placeholder="vous@exemple.com"
                    className={`auth-input${errors.email ? ' error' : ''}`}
                    value={email}
                    onChange={e => { setEmail(e.target.value); setErrors(p => ({ ...p, email: '' })); }}
                  />
                </div>
                {errors.email && (
                  <span className="auth-field-error"><IconAlert /> {errors.email}</span>
                )}
              </div>

              {/* Mot de passe */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="login-pw">Mot de passe</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconLock /></span>
                  <input
                    id="login-pw"
                    type={showPw ? 'text' : 'password'}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    className={`auth-input${errors.password ? ' error' : ''}`}
                    value={password}
                    onChange={e => { setPassword(e.target.value); setErrors(p => ({ ...p, password: '' })); }}
                  />
                  <button
                    type="button"
                    className="auth-toggle-pw"
                    onClick={() => setShowPw(v => !v)}
                    aria-label={showPw ? 'Masquer' : 'Afficher'}
                  >
                    <IconEye off={showPw} />
                  </button>
                </div>
                {errors.password && (
                  <span className="auth-field-error"><IconAlert /> {errors.password}</span>
                )}
              </div>

              {/* Remember + Forgot */}
              <div className="auth-row">
                <label className="auth-checkbox-label">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={e => setRemember(e.target.checked)}
                  />
                  Se souvenir de moi
                </label>
                <button type="button" className="auth-forgot">Mot de passe oublié ?</button>
              </div>

              {/* Submit */}
              <button type="submit" className="auth-btn" disabled={loading}>
                {loading ? (
                  <><span className="auth-spinner" /> Connexion en cours…</>
                ) : (
                  'Se connecter'
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <p className="auth-footer">
            Pas encore de compte ?{' '}
            <button onClick={() => history.push('/register')}>Créer un compte</button>
          </p>

        </div>
      </IonContent>
    </IonPage>
  );
};

export default Login;
