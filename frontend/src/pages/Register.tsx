import React, { useState } from 'react';
import { IonPage, IonContent } from '@ionic/react';
import { useHistory } from 'react-router-dom';
import { register, AuthApiError } from '../services/auth';
import './Auth.css';

// ─── Inline SVG icons ────────────────────────────────────────
const IconStore = () => (
  <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const IconUser = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
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

const IconBuilding = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="2" width="18" height="20" rx="1"/>
    <path d="M9 22V12h6v10M9 7h1M14 7h1M9 11h1M14 11h1"/>
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

const IconCheck = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

// ─── Password strength ────────────────────────────────────────
type Strength = 0 | 1 | 2 | 3;

const getStrength = (pw: string): Strength => {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8)            score++;
  if (/[A-Z]/.test(pw))         score++;
  if (/[0-9]/.test(pw))         score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 3) as Strength;
};

const strengthMeta: Record<Strength, { label: string; color: string; pct: string }> = {
  0: { label: '',         color: 'transparent',   pct: '0%'   },
  1: { label: 'Faible',   color: '#dc2626',        pct: '33%'  },
  2: { label: 'Moyen',    color: '#b45309',        pct: '66%'  },
  3: { label: 'Fort',     color: '#15803d',        pct: '100%' },
};

// ─── Validation ───────────────────────────────────────────────
interface Fields {
  firstName: string; lastName: string;
  storeName: string; email: string;
  password: string;  confirm: string;
}

type FieldErrors = Partial<Record<keyof Fields, string>>;

const validate = (f: Fields): FieldErrors => {
  const e: FieldErrors = {};
  if (!f.firstName.trim()) e.firstName = 'Prénom requis';
  if (!f.lastName.trim())  e.lastName  = 'Nom requis';
  if (!f.storeName.trim()) e.storeName = 'Nom du commerce requis';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email))
    e.email = 'Adresse e-mail invalide';
  if (f.password.length < 6)
    e.password = 'Minimum 6 caractères';
  if (f.confirm !== f.password)
    e.confirm = 'Les mots de passe ne correspondent pas';
  return e;
};

// ─── Component ───────────────────────────────────────────────
const Register: React.FC = () => {
  const history = useHistory();

  const [fields, setFields] = useState<Fields>({
    firstName: '', lastName: '', storeName: '',
    email: '', password: '', confirm: '',
  });
  const [showPw, setShowPw]         = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors]         = useState<FieldErrors>({});
  const [loading, setLoading]       = useState(false);
  const [globalErr, setGlobalErr]   = useState('');
  const [done, setDone]             = useState(false);

  const set = (k: keyof Fields) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFields(p => ({ ...p, [k]: e.target.value }));
    setErrors(p => ({ ...p, [k]: '' }));
  };

  const strength = getStrength(fields.password);
  const sm = strengthMeta[strength];

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setGlobalErr('');
    const errs = validate(fields);
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    try {
      await register(fields);
      setDone(true);
    } catch (err) {
      if (err instanceof AuthApiError) {
        if (Object.keys(err.fieldErrors).length) {
          // Erreurs de validation par champ (ex: e-mail déjà utilisé) →
          // affichées directement sous le champ concerné, comme la validation locale.
          setErrors(prev => ({ ...prev, ...err.fieldErrors }));
        } else {
          setGlobalErr(err.message);
        }
      } else {
        setGlobalErr('Inscription impossible. Réessayez dans un moment.');
      }
    } finally {
      setLoading(false);
    }
  };

  // ─── Success screen ────────────────────────────────────────
  if (done) {
    return (
      <IonPage className="auth-page">
        <IonContent className="auth-scroll" scrollY>
          <div className="auth-content">
            <div className="auth-brand">
              <div className="auth-logo-ring"><IconStore /></div>
              <span className="auth-brand-name">Anavid</span>
              <span className="auth-brand-tag">Smart Retail Platform</span>
            </div>
            <div className="auth-success-card">
              <div className="auth-success-icon"><IconCheck /></div>
              <h2 className="auth-success-title">Compte créé !</h2>
              <p className="auth-success-text">
                Votre commerce <strong>{fields.storeName}</strong> est prêt.<br/>
                Vous êtes maintenant connecté.
              </p>
              <button className="auth-btn" style={{ marginTop: 8 }}
                onClick={() => history.replace('/dashboard')}>
                Accéder à mon tableau de bord
              </button>
            </div>
          </div>
        </IonContent>
      </IonPage>
    );
  }

  // ─── Form screen ──────────────────────────────────────────
  return (
    <IonPage className="auth-page">
      <IonContent className="auth-scroll" scrollY>
        <div className="auth-content">

          {/* Brand */}
          <div className="auth-brand">
            <div className="auth-logo-ring"><IconStore /></div>
            <span className="auth-brand-name">Anavid</span>
            <span className="auth-brand-tag">Smart Retail Platform</span>
          </div>

          {/* Card */}
          <div className="auth-card">
            <h1 className="auth-card-title">Créer un compte</h1>
            <p className="auth-card-subtitle">Analysez vos données retail en quelques secondes.</p>

            {globalErr && (
              <div className="auth-alert" style={{ marginBottom: 16 }}>
                <IconAlert /> {globalErr}
              </div>
            )}

            <form className="auth-form" onSubmit={handleSubmit} noValidate>

              {/* Prénom / Nom */}
              <div className="auth-fields-row">
                <div className="auth-field">
                  <label className="auth-label" htmlFor="reg-first">Prénom</label>
                  <div className="auth-input-wrap">
                    <span className="auth-input-icon"><IconUser /></span>
                    <input id="reg-first" type="text" autoComplete="given-name"
                      placeholder="Ali"
                      className={`auth-input${errors.firstName ? ' error' : ''}`}
                      value={fields.firstName} onChange={set('firstName')} />
                  </div>
                  {errors.firstName && (
                    <span className="auth-field-error"><IconAlert /> {errors.firstName}</span>
                  )}
                </div>

                <div className="auth-field">
                  <label className="auth-label" htmlFor="reg-last">Nom</label>
                  <div className="auth-input-wrap">
                    <span className="auth-input-icon"><IconUser /></span>
                    <input id="reg-last" type="text" autoComplete="family-name"
                      placeholder="Ben Salem"
                      className={`auth-input${errors.lastName ? ' error' : ''}`}
                      value={fields.lastName} onChange={set('lastName')} />
                  </div>
                  {errors.lastName && (
                    <span className="auth-field-error"><IconAlert /> {errors.lastName}</span>
                  )}
                </div>
              </div>

              {/* Nom du commerce */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="reg-store">Nom du commerce</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconBuilding /></span>
                  <input id="reg-store" type="text" autoComplete="organization"
                    placeholder="Boutique El Amal"
                    className={`auth-input${errors.storeName ? ' error' : ''}`}
                    value={fields.storeName} onChange={set('storeName')} />
                </div>
                {errors.storeName && (
                  <span className="auth-field-error"><IconAlert /> {errors.storeName}</span>
                )}
              </div>

              {/* Email */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="reg-email">Adresse e-mail</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconMail /></span>
                  <input id="reg-email" type="email" autoComplete="email"
                    placeholder="vous@exemple.com"
                    className={`auth-input${errors.email ? ' error' : ''}`}
                    value={fields.email} onChange={set('email')} />
                </div>
                {errors.email && (
                  <span className="auth-field-error"><IconAlert /> {errors.email}</span>
                )}
              </div>

              {/* Mot de passe */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="reg-pw">Mot de passe</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconLock /></span>
                  <input id="reg-pw" type={showPw ? 'text' : 'password'}
                    autoComplete="new-password" placeholder="Minimum 6 caractères"
                    className={`auth-input${errors.password ? ' error' : ''}`}
                    value={fields.password} onChange={set('password')} />
                  <button type="button" className="auth-toggle-pw"
                    onClick={() => setShowPw(v => !v)}
                    aria-label={showPw ? 'Masquer' : 'Afficher'}>
                    <IconEye off={showPw} />
                  </button>
                </div>
                {errors.password && (
                  <span className="auth-field-error"><IconAlert /> {errors.password}</span>
                )}
                {/* Strength bar */}
                {fields.password && (
                  <div className="auth-strength">
                    <div className="auth-strength-bar">
                      <div className="auth-strength-fill"
                        style={{ width: sm.pct, background: sm.color }} />
                    </div>
                    {sm.label && (
                      <span className="auth-strength-label"
                        style={{ color: sm.color }}>Force : {sm.label}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Confirmation */}
              <div className="auth-field">
                <label className="auth-label" htmlFor="reg-confirm">Confirmer le mot de passe</label>
                <div className="auth-input-wrap">
                  <span className="auth-input-icon"><IconLock /></span>
                  <input id="reg-confirm" type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password" placeholder="••••••••"
                    className={`auth-input${errors.confirm ? ' error' : ''}`}
                    value={fields.confirm} onChange={set('confirm')} />
                  <button type="button" className="auth-toggle-pw"
                    onClick={() => setShowConfirm(v => !v)}
                    aria-label={showConfirm ? 'Masquer' : 'Afficher'}>
                    <IconEye off={showConfirm} />
                  </button>
                </div>
                {errors.confirm && (
                  <span className="auth-field-error"><IconAlert /> {errors.confirm}</span>
                )}
              </div>

              {/* CGU */}
              <div className="auth-row" style={{ justifyContent: 'flex-start', gap: 8 }}>
                <label className="auth-checkbox-label">
                  <input type="checkbox" required />
                  J'accepte les <button type="button" className="auth-forgot" style={{ fontWeight: 500 }}>
                    conditions d'utilisation
                  </button>
                </label>
              </div>

              {/* Submit */}
              <button type="submit" className="auth-btn" disabled={loading}>
                {loading ? (
                  <><span className="auth-spinner" /> Création en cours…</>
                ) : (
                  'Créer mon compte'
                )}
              </button>
            </form>
          </div>

          {/* Footer */}
          <p className="auth-footer">
            Déjà un compte ?{' '}
            <button onClick={() => history.push('/login')}>Se connecter</button>
          </p>

        </div>
      </IonContent>
    </IonPage>
  );
};

export default Register;
