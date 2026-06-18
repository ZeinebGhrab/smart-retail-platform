import React, { useState } from 'react';
import { IonPage, IonContent } from '@ionic/react';
import { useHistory } from 'react-router-dom';
import { login, AuthApiError, requestPasswordReset, verifyResetCode, confirmPasswordReset } from '../services/auth';
import './Auth.css';

// ─── Inline SVG icons ────────────────────────────────────────
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
const IconCheck = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const IconBack = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6"/>
  </svg>
);

// ─── Validation ──────────────────────────────────────────────
const validateEmail    = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? '' : 'Adresse e-mail invalide';
const validatePassword = (v: string) => v.length < 6 ? 'Minimum 6 caractères' : '';

// ─── Types ───────────────────────────────────────────────────
type ForgotStep = 'email' | 'otp' | 'newpw' | 'done';

// ─── Component ───────────────────────────────────────────────
const Login: React.FC = () => {
  const history = useHistory();

  // ── Login state
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [showPw, setShowPw]       = useState(false);
  const [remember, setRemember]   = useState(false);
  const [loading, setLoading]     = useState(false);
  const [globalErr, setGlobalErr] = useState('');
  const [errors, setErrors]       = useState<{ email: string; password: string }>({ email: '', password: '' });

  // ── Forgot password state
  const [forgotOpen,   setForgotOpen]   = useState(false);
  const [forgotStep,   setForgotStep]   = useState<ForgotStep>('email');
  const [fpEmail,      setFpEmail]      = useState('');
  const [fpCode,       setFpCode]       = useState('');
  const [fpPassword,   setFpPassword]   = useState('');
  const [fpConfirm,    setFpConfirm]    = useState('');
  const [fpShowPw,     setFpShowPw]     = useState(false);
  const [fpShowPw2,    setFpShowPw2]    = useState(false);
  const [fpLoading,    setFpLoading]    = useState(false);
  const [fpErr,        setFpErr]        = useState('');
  const [fpFieldErrs,  setFpFieldErrs]  = useState<Record<string, string>>({});

  // ── Login submit
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
      await login(email, password, remember);
      history.replace('/dashboard');
    } catch (err) {
      setGlobalErr(err instanceof AuthApiError ? err.message : 'Connexion impossible. Réessayez dans un moment.');
    } finally {
      setLoading(false);
    }
  };

  // ── Open / reset forgot flow
  const openForgot = () => {
    setFpEmail(email); // pré-remplir avec l'email de la form login si déjà saisi
    setFpCode('');
    setFpPassword('');
    setFpConfirm('');
    setFpErr('');
    setFpFieldErrs({});
    setForgotStep('email');
    setForgotOpen(true);
  };
  const closeForgot = () => setForgotOpen(false);

  // ── Étape 1 : demande OTP
  const handleFpRequest = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const emailErr = validateEmail(fpEmail);
    if (emailErr) { setFpFieldErrs({ email: emailErr }); return; }
    setFpFieldErrs({});
    setFpErr('');
    setFpLoading(true);
    try {
      await requestPasswordReset(fpEmail);
      setForgotStep('otp');
    } catch (err) {
      if (err instanceof AuthApiError && err.status === 404) {
        setFpFieldErrs({ email: "Aucun compte n'est associé à cette adresse e-mail." });
      } else {
        setFpErr(err instanceof AuthApiError ? err.message : 'Une erreur est survenue.');
      }
    } finally {
      setFpLoading(false);
    }
  };

  // ── Étape 2 : vérification OTP
  const handleFpVerify = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (fpCode.length !== 6) { setFpFieldErrs({ code: 'Le code doit contenir 6 chiffres' }); return; }
    setFpFieldErrs({});
    setFpErr('');
    setFpLoading(true);
    try {
      await verifyResetCode(fpEmail, fpCode);
      setForgotStep('newpw');
    } catch (err) {
      setFpErr(err instanceof AuthApiError ? err.message : 'Code invalide.');
    } finally {
      setFpLoading(false);
    }
  };

  // ── Étape 3 : nouveau mot de passe
  const handleFpConfirm = async (ev: React.FormEvent) => {
    ev.preventDefault();
    const errs: Record<string, string> = {};
    const pwErr = validatePassword(fpPassword);
    if (pwErr) errs.password = pwErr;
    if (fpPassword !== fpConfirm) errs.confirm = 'Les mots de passe ne correspondent pas.';
    if (Object.keys(errs).length) { setFpFieldErrs(errs); return; }
    setFpFieldErrs({});
    setFpErr('');
    setFpLoading(true);
    try {
      await confirmPasswordReset(fpEmail, fpCode, fpPassword, fpConfirm);
      setForgotStep('done');
    } catch (err) {
      setFpErr(err instanceof AuthApiError ? err.message : 'Une erreur est survenue.');
    } finally {
      setFpLoading(false);
    }
  };

  // ── OTP input handler : chiffres seulement, max 6
  const handleOtpChange = (v: string) => {
    const clean = v.replace(/\D/g, '').slice(0, 6);
    setFpCode(clean);
    setFpFieldErrs({});
  };

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

          {/* ════════════════════════════════════════════
              FORGOT PASSWORD FLOW (overlay inline)
              ════════════════════════════════════════════ */}
          {forgotOpen ? (
            <div className="auth-card fp-card">

              {/* Étape 1 — Saisie de l'adresse e-mail */}
              {forgotStep === 'email' && (
                <>
                  <button className="fp-back" onClick={closeForgot} aria-label="Retour"><IconBack /> Retour</button>
                  <div className="fp-header">
                    <div className="fp-icon-ring fp-icon-blue">
                      <IconMail />
                    </div>
                    <h2 className="auth-card-title">Mot de passe oublié</h2>
                    <p className="auth-card-subtitle">Entrez votre adresse e-mail pour recevoir un code de vérification.</p>
                  </div>
                  {fpErr && <div className="auth-alert" style={{ marginBottom: 16 }}><IconAlert /> {fpErr}</div>}
                  <form className="auth-form" onSubmit={handleFpRequest} noValidate>
                    <div className="auth-field">
                      <label className="auth-label" htmlFor="fp-email">Adresse e-mail</label>
                      <div className="auth-input-wrap">
                        <span className="auth-input-icon"><IconMail /></span>
                        <input
                          id="fp-email" type="email" autoComplete="email"
                          placeholder="vous@exemple.com"
                          className={`auth-input${fpFieldErrs.email ? ' error' : ''}`}
                          value={fpEmail}
                          onChange={e => { setFpEmail(e.target.value); setFpFieldErrs({}); }}
                        />
                      </div>
                      {fpFieldErrs.email && <span className="auth-field-error"><IconAlert /> {fpFieldErrs.email}</span>}
                    </div>
                    <button type="submit" className="auth-btn" disabled={fpLoading}>
                      {fpLoading ? <><span className="auth-spinner" /> Envoi…</> : 'Envoyer le code'}
                    </button>
                  </form>
                </>
              )}

              {/* Étape 2 — Saisie du code OTP */}
              {forgotStep === 'otp' && (
                <>
                  <button className="fp-back" onClick={() => setForgotStep('email')} aria-label="Retour"><IconBack /> Retour</button>
                  <div className="fp-header">
                    <div className="fp-icon-ring fp-icon-blue">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>
                      </svg>
                    </div>
                    <h2 className="auth-card-title">Vérification</h2>
                    <p className="auth-card-subtitle">
                      Entrez le code à 6 chiffres envoyé à<br/>
                      <strong>{fpEmail}</strong>
                    </p>

                  </div>
                  {fpErr && <div className="auth-alert" style={{ marginBottom: 16 }}><IconAlert /> {fpErr}</div>}
                  <form className="auth-form" onSubmit={handleFpVerify} noValidate>
                    <div className="auth-field">
                      <label className="auth-label" htmlFor="fp-otp">Code de vérification</label>
                      <input
                        id="fp-otp" type="text" inputMode="numeric" autoComplete="one-time-code"
                        placeholder="_ _ _ _ _ _"
                        className={`auth-input fp-otp-input${fpFieldErrs.code ? ' error' : ''}`}
                        value={fpCode}
                        onChange={e => handleOtpChange(e.target.value)}
                        maxLength={6}
                      />
                      {fpFieldErrs.code && <span className="auth-field-error"><IconAlert /> {fpFieldErrs.code}</span>}
                    </div>
                    <button type="submit" className="auth-btn" disabled={fpLoading || fpCode.length !== 6}>
                      {fpLoading ? <><span className="auth-spinner" /> Vérification…</> : 'Vérifier le code'}
                    </button>
                    <button type="button" className="fp-resend" onClick={() => { setFpCode(''); setForgotStep('email'); }}>
                      Renvoyer un code
                    </button>
                  </form>
                </>
              )}

              {/* Étape 3 — Nouveau mot de passe */}
              {forgotStep === 'newpw' && (
                <>
                  <div className="fp-header">
                    <div className="fp-icon-ring fp-icon-blue">
                      <IconLock />
                    </div>
                    <h2 className="auth-card-title">Nouveau mot de passe</h2>
                    <p className="auth-card-subtitle">Choisissez un mot de passe d'au moins 6 caractères.</p>
                  </div>
                  {fpErr && <div className="auth-alert" style={{ marginBottom: 16 }}><IconAlert /> {fpErr}</div>}
                  <form className="auth-form" onSubmit={handleFpConfirm} noValidate>
                    <div className="auth-field">
                      <label className="auth-label" htmlFor="fp-pw">Nouveau mot de passe</label>
                      <div className="auth-input-wrap">
                        <span className="auth-input-icon"><IconLock /></span>
                        <input
                          id="fp-pw" type={fpShowPw ? 'text' : 'password'}
                          autoComplete="new-password" placeholder="••••••••"
                          className={`auth-input${fpFieldErrs.password ? ' error' : ''}`}
                          value={fpPassword}
                          onChange={e => { setFpPassword(e.target.value); setFpFieldErrs(p => ({ ...p, password: '' })); }}
                        />
                        <button type="button" className="auth-toggle-pw" onClick={() => setFpShowPw(v => !v)} aria-label={fpShowPw ? 'Masquer' : 'Afficher'}>
                          <IconEye off={fpShowPw} />
                        </button>
                      </div>
                      {fpFieldErrs.password && <span className="auth-field-error"><IconAlert /> {fpFieldErrs.password}</span>}
                    </div>
                    <div className="auth-field">
                      <label className="auth-label" htmlFor="fp-confirm">Confirmer le mot de passe</label>
                      <div className="auth-input-wrap">
                        <span className="auth-input-icon"><IconLock /></span>
                        <input
                          id="fp-confirm" type={fpShowPw2 ? 'text' : 'password'}
                          autoComplete="new-password" placeholder="••••••••"
                          className={`auth-input${fpFieldErrs.confirm ? ' error' : ''}`}
                          value={fpConfirm}
                          onChange={e => { setFpConfirm(e.target.value); setFpFieldErrs(p => ({ ...p, confirm: '' })); }}
                        />
                        <button type="button" className="auth-toggle-pw" onClick={() => setFpShowPw2(v => !v)} aria-label={fpShowPw2 ? 'Masquer' : 'Afficher'}>
                          <IconEye off={fpShowPw2} />
                        </button>
                      </div>
                      {fpFieldErrs.confirm && <span className="auth-field-error"><IconAlert /> {fpFieldErrs.confirm}</span>}
                    </div>
                    <button type="submit" className="auth-btn" disabled={fpLoading}>
                      {fpLoading ? <><span className="auth-spinner" /> Enregistrement…</> : 'Enregistrer le mot de passe'}
                    </button>
                  </form>
                </>
              )}

              {/* Étape 4 — Succès */}
              {forgotStep === 'done' && (
                <div className="fp-success">
                  <div className="auth-success-icon"><IconCheck /></div>
                  <h2 className="auth-success-title">Mot de passe modifié !</h2>
                  <p className="auth-success-text">Votre mot de passe a été mis à jour avec succès. Vous pouvez maintenant vous connecter.</p>
                  <button
                    className="auth-btn"
                    style={{ marginTop: 8 }}
                    onClick={() => { closeForgot(); setEmail(fpEmail); }}
                  >
                    Se connecter
                  </button>
                </div>
              )}
            </div>

          ) : (
            /* ════════════════════════════════════════════
               LOGIN FORM
               ════════════════════════════════════════════ */
            <div className="auth-card">
              <h1 className="auth-card-title">Connexion</h1>
              <p className="auth-card-subtitle">Bienvenue ! Accédez à votre tableau de bord.</p>

              {globalErr && (
                <div className="auth-alert" style={{ marginBottom: 16 }}>
                  <IconAlert /> {globalErr}
                </div>
              )}

              <form className="auth-form" onSubmit={handleSubmit} noValidate>
                <div className="auth-field">
                  <label className="auth-label" htmlFor="login-email">Adresse e-mail</label>
                  <div className="auth-input-wrap">
                    <span className="auth-input-icon"><IconMail /></span>
                    <input
                      id="login-email" type="email" autoComplete="email"
                      placeholder="vous@exemple.com"
                      className={`auth-input${errors.email ? ' error' : ''}`}
                      value={email}
                      onChange={e => { setEmail(e.target.value); setErrors(p => ({ ...p, email: '' })); }}
                    />
                  </div>
                  {errors.email && <span className="auth-field-error"><IconAlert /> {errors.email}</span>}
                </div>

                <div className="auth-field">
                  <label className="auth-label" htmlFor="login-pw">Mot de passe</label>
                  <div className="auth-input-wrap">
                    <span className="auth-input-icon"><IconLock /></span>
                    <input
                      id="login-pw" type={showPw ? 'text' : 'password'}
                      autoComplete="current-password" placeholder="••••••••"
                      className={`auth-input${errors.password ? ' error' : ''}`}
                      value={password}
                      onChange={e => { setPassword(e.target.value); setErrors(p => ({ ...p, password: '' })); }}
                    />
                    <button type="button" className="auth-toggle-pw" onClick={() => setShowPw(v => !v)} aria-label={showPw ? 'Masquer' : 'Afficher'}>
                      <IconEye off={showPw} />
                    </button>
                  </div>
                  {errors.password && <span className="auth-field-error"><IconAlert /> {errors.password}</span>}
                </div>

                <div className="auth-row">
                  <label className="auth-checkbox-label">
                    <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
                    Se souvenir de moi
                  </label>
                  <button type="button" className="auth-forgot" onClick={openForgot}>
                    Mot de passe oublié ?
                  </button>
                </div>

                <button type="submit" className="auth-btn" disabled={loading}>
                  {loading ? <><span className="auth-spinner" /> Connexion en cours…</> : 'Se connecter'}
                </button>
              </form>
            </div>
          )}

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