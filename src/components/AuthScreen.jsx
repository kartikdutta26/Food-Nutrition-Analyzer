import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, LockKeyhole, Mail, Salad, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { friendlyAuthError, getRegistrationSuccessMessage } from '../lib/authFlows.js';

const initialFields = { name: '', email: '', password: '', confirmPassword: '' };

const modeCopy = {
  login: {
    eyebrow: 'Welcome back',
    title: 'Sign in to NutriAI',
    description: 'Access your personal nutrition space and saved preferences.',
    submit: 'Sign in',
  },
  signup: {
    eyebrow: 'A fresh start',
    title: 'Create your account',
    description: 'Save your nutrition preferences and keep your journey in one place.',
    submit: 'Create account',
  },
  forgot: {
    eyebrow: 'Account recovery',
    title: 'Reset your password',
    description: 'Enter your account email and we’ll send a secure reset link.',
    submit: 'Send reset email',
  },
  reset: {
    eyebrow: 'Choose a new password',
    title: 'Finish password reset',
    description: 'Set a new password for your NutriAI account.',
    submit: 'Update password',
  },
  verify: {
    eyebrow: 'Email confirmation',
    title: 'Confirm your email',
    description: 'Review this request and confirm the email address associated with your NutriAI account.',
    submit: 'Confirm email',
  },
};

function FormField({ id, label, type = 'text', value, onChange, autoComplete, minLength, maxLength, icon: Icon }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-600">
        {label}
      </label>
      <div className="relative">
        {Icon && <Icon aria-hidden="true" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-teal-700/65" />}
        <input
          id={id}
          name={id}
          type={type}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          minLength={minLength}
          maxLength={maxLength}
          required
          className={`w-full rounded-xl border border-slate-200 bg-white/75 py-3 text-sm font-medium text-slate-800 outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-500/20 ${Icon ? 'pl-10 pr-4' : 'px-4'}`}
        />
      </div>
    </div>
  );
}

export default function AuthScreen({
  mode = 'login',
  onModeChange,
  onRegister,
  onLogin,
  onResendVerification,
  onConfirmEmail,
  onForgotPassword,
  onResetPassword,
  onAuthenticated,
  onPasswordResetComplete,
  authLoading = false,
  recoveryReady = false,
  redirectNotice = '',
  redirectError = '',
  onExploreFood,
}) {
  const [fields, setFields] = useState(initialFields);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const copy = modeCopy[mode] || modeCopy.login;
  const isResetLinkChecking = mode === 'reset' && !recoveryReady && !redirectError;

  const changeMode = (nextMode) => {
    setErrorMessage('');
    setSuccessMessage('');
    onModeChange?.(nextMode);
  };

  const updateField = (field) => (event) => {
    setFields((previous) => ({ ...previous, [field]: event.target.value }));
    setErrorMessage('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    if (mode === 'login') onModeChange?.('login');

    const email = fields.email.trim().toLowerCase();
    const password = fields.password;

    if (mode === 'verify') {
      setIsSubmitting(true);
      try {
        const result = await onConfirmEmail?.();
        if (!result?.verified) throw new Error('Supabase did not confirm this email address.');
        if (result.authenticated) onAuthenticated?.('Your email was confirmed successfully. Welcome to NutriAI.');
        else setSuccessMessage('Email confirmed successfully. Sign in to continue.');
      } catch (error) {
        setErrorMessage(friendlyAuthError(error, 'verify'));
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    if (mode !== 'reset' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setErrorMessage('Enter a valid email address.');
      return;
    }

    if (mode === 'signup') {
      if (fields.name.trim().length < 2) {
        setErrorMessage('Enter your name using at least two characters.');
        return;
      }
      if (password.length < 8) {
        setErrorMessage('Use a password with at least 8 characters.');
        return;
      }
      if (password !== fields.confirmPassword) {
        setErrorMessage('The passwords do not match.');
        return;
      }
    }

    if (mode === 'login' && !password) {
      setErrorMessage('Enter your password to sign in.');
      return;
    }

    if (mode === 'reset' && !recoveryReady) {
      setErrorMessage('Open the latest password reset email to continue.');
      return;
    }

    if (mode === 'reset') {
      if (password.length < 8) {
        setErrorMessage('Use a password with at least 8 characters.');
        return;
      }
      if (password !== fields.confirmPassword) {
        setErrorMessage('The passwords do not match.');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (mode === 'signup') {
        const result = await onRegister({
          name: fields.name.trim(),
          email,
          password,
        });

        if (result?.authenticated) {
          onAuthenticated?.();
          return;
        }

        setFields((previous) => ({ ...previous, password: '', confirmPassword: '' }));
        changeMode('login');
        setSuccessMessage(getRegistrationSuccessMessage(email, result));
        return;
      }

      if (mode === 'login') {
        await onLogin({ email, password });
        onAuthenticated?.();
        return;
      }

      if (mode === 'forgot') {
        await onForgotPassword(email);
        setFields((previous) => ({ ...previous, password: '', confirmPassword: '' }));
        changeMode('login');
        setSuccessMessage('If an account exists for that email, a password reset link is on its way.');
        return;
      }

      if (mode === 'reset') {
        await onResetPassword(password);
        setFields((previous) => ({ ...previous, password: '', confirmPassword: '' }));
        setSuccessMessage('Your password has been updated. You can continue to NutriAI.');
        onPasswordResetComplete?.();
      }
    } catch (error) {
      setErrorMessage(friendlyAuthError(error, mode));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendVerification = async () => {
    setErrorMessage('');
    setSuccessMessage('');
    onModeChange?.('login');
    const email = fields.email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setErrorMessage('Enter your email address above before requesting another confirmation email.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onResendVerification?.(email);
      setSuccessMessage('If that address has an unconfirmed account, a new confirmation email has been requested.');
    } catch (error) {
      setErrorMessage(friendlyAuthError(error, 'resend'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl px-4 py-10 sm:px-6 sm:py-14">
      <section aria-labelledby="auth-title" className="overflow-hidden rounded-[30px] border border-white/80 bg-white/80 shadow-[0_24px_70px_rgba(23,74,71,.12)] backdrop-blur-xl">
        <div className="border-b border-teal-100/80 bg-gradient-to-br from-teal-50/90 via-white/70 to-orange-50/70 px-6 py-7 text-center sm:px-10 sm:py-9">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white bg-white/80 text-teal-800 shadow-sm">
            <Salad size={26} strokeWidth={1.7} aria-hidden="true" />
          </div>
          <p className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/90 bg-white/65 px-3 py-1.5 text-[10px] font-extrabold uppercase tracking-[.16em] text-teal-800">
            <Sparkles size={13} aria-hidden="true" /> {copy.eyebrow}
          </p>
          <h1 id="auth-title" className="mt-2 text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">{copy.title}</h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate-600">{copy.description}</p>
        </div>

        <div className="space-y-5 px-6 py-6 sm:px-10 sm:py-8">
          {redirectNotice && <p role="status" className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm leading-relaxed text-teal-900">{redirectNotice}</p>}
          {(redirectError || errorMessage) && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-relaxed text-rose-800">{redirectError || errorMessage}</p>}
          {successMessage && <p role="status" className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-relaxed text-emerald-900"><CheckCircle2 size={17} className="mt-0.5 shrink-0" aria-hidden="true" />{successMessage}</p>}
          {authLoading && <p role="status" className="rounded-xl border border-teal-100 bg-teal-50/70 px-4 py-3 text-center text-xs font-semibold text-teal-900">Restoring your account session…</p>}

          {mode === 'verify' ? (
            <div className="space-y-4 rounded-2xl border border-teal-100 bg-teal-50/60 p-5 text-center">
              <p className="text-sm leading-relaxed text-slate-700">The link is ready for confirmation. Supabase will verify it only after you press the button.</p>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting || authLoading || !onConfirmEmail}
                className="flex min-h-12 w-full items-center justify-center gap-2 rounded-full border border-white/80 bg-gradient-to-r from-orange-200 via-orange-100 to-teal-200 px-5 py-3 text-sm font-extrabold text-teal-950 shadow-sm disabled:cursor-wait disabled:opacity-60"
              >
                {isSubmitting ? 'Please wait…' : authLoading ? 'Checking account…' : copy.submit}
              </button>
              <button type="button" onClick={() => changeMode('login')} className="text-xs font-bold text-slate-500 underline underline-offset-4">Return to sign in</button>
            </div>
          ) : isResetLinkChecking ? (
            <div className="rounded-2xl border border-teal-100 bg-teal-50/60 p-5 text-center">
              <p role="status" className="text-sm font-bold text-teal-900">Checking your secure password reset link…</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">Keep this page open while Supabase verifies the link.</p>
            </div>
          ) : mode === 'reset' && redirectError ? (
            <div className="rounded-2xl border border-orange-200 bg-orange-50 p-5 text-center">
              <p className="text-sm font-bold text-orange-900">This reset link needs attention.</p>
              <button type="button" onClick={() => changeMode('forgot')} className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-teal-800 underline underline-offset-4">Request another reset link <ArrowRight size={15} aria-hidden="true" /></button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {mode === 'signup' && (
                <FormField
                  id="auth-name"
                  label="Name"
                  value={fields.name}
                  onChange={updateField('name')}
                  autoComplete="name"
                  maxLength={80}
                  icon={UserRound}
                />
              )}

              {mode !== 'reset' && (
                <FormField
                  id="auth-email"
                  label="Email address"
                  type="email"
                  value={fields.email}
                  onChange={updateField('email')}
                  autoComplete="email"
                  maxLength={254}
                  icon={Mail}
                />
              )}

              {(mode === 'login' || mode === 'signup' || mode === 'reset') && (
                <FormField
                  id="auth-password"
                  label={mode === 'reset' ? 'New password' : 'Password'}
                  type="password"
                  value={fields.password}
                  onChange={updateField('password')}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  minLength={8}
                  maxLength={128}
                  icon={LockKeyhole}
                />
              )}

              {(mode === 'signup' || mode === 'reset') && (
                <FormField
                  id="auth-confirm-password"
                  label="Confirm password"
                  type="password"
                  value={fields.confirmPassword}
                  onChange={updateField('confirmPassword')}
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  icon={LockKeyhole}
                />
              )}

              {mode === 'signup' && (
                <div className="space-y-2 text-xs leading-relaxed text-slate-500">
                  <p>Use at least 8 characters. We’ll send a verification link to your email before your account can access personal features.</p>
                  <p>Email links open at the configured app origin. A localhost link works only on the computer running Vite; use an allowlisted, reachable LAN or deployed origin to confirm on another device.</p>
                </div>
              )}

              {mode === 'login' && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button type="button" onClick={() => changeMode('forgot')} className="text-xs font-bold text-teal-800 underline underline-offset-4 hover:text-teal-950">Forgot password?</button>
                  <button type="button" onClick={handleResendVerification} disabled={isSubmitting || authLoading || !onResendVerification} className="text-xs font-bold text-teal-800 underline underline-offset-4 hover:text-teal-950 disabled:opacity-50">Resend confirmation email</button>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting || authLoading}
                className="flex min-h-12 w-full items-center justify-center gap-2 rounded-full border border-white/80 bg-gradient-to-r from-orange-200 via-orange-100 to-teal-200 px-5 py-3 text-sm font-extrabold text-teal-950 shadow-[0_8px_22px_rgba(23,74,71,.12)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_28px_rgba(23,74,71,.16)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:cursor-wait disabled:opacity-60"
              >
                {isSubmitting ? 'Please wait…' : authLoading ? 'Checking account…' : copy.submit}
                {!isSubmitting && !authLoading && <ArrowRight size={16} aria-hidden="true" />}
              </button>
            </form>
          )}

          {(mode === 'login' || mode === 'signup') && (
            <p className="text-center text-sm text-slate-600">
              {mode === 'signup' ? 'Already have an account?' : 'New to NutriAI?'}{' '}
              <button type="button" onClick={() => changeMode(mode === 'signup' ? 'login' : 'signup')} className="font-extrabold text-teal-800 underline underline-offset-4 hover:text-teal-950">
                {mode === 'signup' ? 'Sign in' : 'Create an account'}
              </button>
            </p>
          )}

          {mode === 'forgot' && <button type="button" onClick={() => changeMode('login')} className="mx-auto flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-teal-800"><ArrowLeft size={14} aria-hidden="true" /> Back to sign in</button>}
          {mode === 'reset' && recoveryReady && successMessage && <button type="button" onClick={() => onPasswordResetComplete?.()} className="mx-auto flex items-center gap-2 text-xs font-bold text-teal-800">Continue to NutriAI <ArrowRight size={14} aria-hidden="true" /></button>}

          {mode === 'reset' && !recoveryReady && (
            <button type="button" onClick={() => changeMode('forgot')} className="mx-auto flex items-center gap-2 text-xs font-bold text-slate-500 hover:text-teal-800"><ArrowLeft size={14} aria-hidden="true" /> Back to password help</button>
          )}

          <div className="border-t border-slate-100 pt-4 text-center">
            <p className="inline-flex items-center justify-center gap-1.5 text-[11px] leading-relaxed text-slate-500"><ShieldCheck size={14} className="text-teal-700" aria-hidden="true" /> Your food analysis stays available without an account.</p>
            {onExploreFood && <button type="button" onClick={onExploreFood} className="mt-2 block w-full text-center text-xs font-bold text-teal-800 underline underline-offset-4">Continue exploring food analysis</button>}
          </div>
        </div>
      </section>
    </div>
  );
}
