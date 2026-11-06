import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  MoonStar,
  Salad,
  ShieldCheck,
  Sparkles,
  SunMedium,
  UserRound,
} from 'lucide-react';
import './auth.css';

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const passwordRequirement = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

export default function AuthPage({ onAuthenticate, onResetPassword, onExploreDemo, authConfigured, theme, onToggleTheme }) {
  const [mode, setMode] = useState('login');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const reducedMotion = useReducedMotion();
  const isSignup = mode === 'signup';

  const changeMode = (nextMode) => {
    setMode(nextMode);
    setFeedback(null);
    setPassword('');
    setConfirmPassword('');
  };

  const validate = () => {
    if (isSignup && !fullName.trim()) return 'Enter your full name.';
    if (!email.trim()) return 'Enter your email address.';
    if (!emailPattern.test(email.trim())) return 'Enter a valid email address.';
    if (!password) return 'Enter your password.';
    if (isSignup && !passwordRequirement.test(password)) {
      return 'Use at least 8 characters, including uppercase, lowercase, and a number.';
    }
    if (isSignup && password !== confirmPassword) return 'Your passwords do not match.';
    return null;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFeedback(null);
    const validationError = validate();
    if (validationError) {
      setFeedback({ type: 'error', message: validationError });
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await onAuthenticate({
        mode,
        fullName: fullName.trim(),
        email: email.trim(),
        password,
      });
      if (result?.message) setFeedback({ type: result.type || 'error', message: result.message });
    } catch (error) {
      setFeedback({ type: 'error', message: error.message || 'Authentication could not be completed. Try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotPassword = async (event) => {
    event.preventDefault();
    setFeedback(null);
    if (!email.trim() || !emailPattern.test(email.trim())) {
      setFeedback({ type: 'error', message: 'Enter a valid email address to reset your password.' });
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await onResetPassword(email.trim());
      if (result?.message) setFeedback({ type: result.type || 'error', message: result.message });
    } catch (error) {
      setFeedback({ type: 'error', message: error.message || 'The reset request could not be completed. Try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-screen">
      <div className="auth-background-effects" aria-hidden="true">
        <span className="auth-wave auth-wave--one" />
        <span className="auth-wave auth-wave--two" />
        <span className="auth-shape auth-shape--diamond" />
        <span className="auth-shape auth-shape--spark" />
        <span className="auth-shape auth-shape--ring" />
        <span className="auth-shape auth-shape--orb" />
        <span className="auth-shape auth-shape--spark auth-shape--spark-small" />
        <span className="auth-particle auth-particle--one" />
        <span className="auth-particle auth-particle--two" />
        <span className="auth-particle auth-particle--three" />
        <span className="auth-particle auth-particle--four" />
        <span className="auth-particle auth-particle--five" />
        <span className="auth-particle auth-particle--six" />
        <span className="auth-particle auth-particle--seven" />
        <span className="auth-particle auth-particle--eight" />
        <span className="auth-particle auth-particle--nine" />
        <span className="auth-particle auth-particle--ten" />
      </div>
      <motion.section
        className="auth-card"
        initial={reducedMotion ? false : { opacity: 0, y: 22, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        aria-label="NutriAI account access"
      >
        <section className="auth-form-panel" aria-label={isSignup ? 'Create your account' : 'Sign in to your account'}>
          <div className="auth-panel-header">
            <button type="button" className="auth-theme-toggle" onClick={onToggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              {theme === 'dark' ? <SunMedium size={15} /> : <MoonStar size={15} />}
              <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>
            <motion.div
              className="auth-brand"
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.08 }}
            >
              <span className="auth-brand-mark"><Salad size={21} strokeWidth={1.8} /></span>
              <span className="auth-brand-word">Nutri<span>AI</span><small>INTELLIGENT NUTRITION</small></span>
            </motion.div>
          </div>
          <motion.div
            className="auth-form-heading"
            initial={reducedMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.42, delay: 0.18 }}
          >
            <span className="auth-form-kicker">WELCOME TO YOUR WELLNESS SPACE</span>
            <h2>{isSignup ? 'Create your account' : 'Welcome back'}</h2>
            <p>{isSignup ? 'A healthier routine starts with a simple step.' : 'Your next healthy choice starts right here.'}</p>
          </motion.div>

          <motion.div
            className="auth-tabs"
            role="tablist"
            aria-label="Choose login or sign up"
            initial={reducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.38, delay: 0.28 }}
          >
            <button type="button" role="tab" aria-selected={!isSignup} className={!isSignup ? 'is-selected' : ''} onClick={() => changeMode('login')}>Login</button>
            <button type="button" role="tab" aria-selected={isSignup} className={isSignup ? 'is-selected' : ''} onClick={() => changeMode('signup')}>Sign Up</button>
          </motion.div>

          <motion.div
            className="auth-setup-note"
            role="status"
            initial={reducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.38, delay: 0.34 }}
          >
            <span className="auth-setup-dot" />
            {authConfigured ? 'Secure sign-in powered by Supabase.' : 'Add your Supabase project settings to enable accounts.'}
          </motion.div>

          <AnimatePresence mode="wait" initial={false}>
            <motion.form
              key={mode}
              className="auth-form"
              onSubmit={handleSubmit}
              initial={reducedMotion ? false : { opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reducedMotion ? undefined : { opacity: 0, y: -5 }}
              transition={{ duration: 0.2 }}
              noValidate
            >
              {isSignup && (
                <motion.label
                  className="auth-field"
                  initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.03 }}
                >
                  <span>Full name</span>
                  <span className="auth-input-wrap">
                    <UserRound size={17} aria-hidden="true" />
                    <input autoComplete="name" name="name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="How should we call you?" />
                  </span>
                </motion.label>
              )}
              <motion.label
                className="auth-field"
                initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: isSignup ? 0.08 : 0.03 }}
              >
                <span>Email address</span>
                <span className="auth-input-wrap">
                  <Mail size={17} aria-hidden="true" />
                  <input autoComplete="email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
                </span>
              </motion.label>
              <motion.label
                className="auth-field"
                initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: isSignup ? 0.13 : 0.08 }}
              >
                <span>Password</span>
                <span className="auth-input-wrap">
                  <LockKeyhole size={17} aria-hidden="true" />
                  <input autoComplete={isSignup ? 'new-password' : 'current-password'} name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isSignup ? 'Create a strong password' : 'Enter your password'} />
                  <button className="auth-password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
                {isSignup && <small className="auth-hint">8+ characters with uppercase, lowercase, and a number.</small>}
              </motion.label>
              {isSignup && (
                <motion.label
                  className="auth-field"
                  initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.18 }}
                >
                  <span>Confirm password</span>
                  <span className="auth-input-wrap">
                    <LockKeyhole size={17} aria-hidden="true" />
                    <input autoComplete="new-password" name="confirm-password" type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" />
                  </span>
                </motion.label>
              )}

              {!isSignup && (
                <motion.div
                  className="auth-forgot-row"
                  initial={reducedMotion ? false : { opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3, delay: 0.14 }}
                >
                  <span>Forgot your password?</span>
                  <button type="button" onClick={handleForgotPassword} disabled={isSubmitting}>Reset it</button>
                </motion.div>
              )}

              {feedback && (
                <div className={`auth-feedback auth-feedback--${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>
                  {feedback.message}
                </div>
              )}

              <motion.button
                className="auth-submit"
                type="submit"
                disabled={isSubmitting}
                initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.32, delay: isSignup ? 0.24 : 0.19 }}
              >
                {isSubmitting ? <span className="auth-spinner" aria-hidden="true" /> : <>{isSignup ? 'Create account' : 'Login'} <ArrowRight size={17} /></>}
                <span className="sr-only">{isSubmitting ? 'Please wait' : ''}</span>
              </motion.button>
              <p className="auth-terms">A healthier routine starts with choices that work for you.</p>
            </motion.form>
          </AnimatePresence>

          {onExploreDemo && (
            <motion.div
              className="auth-demo-entry"
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.56 }}
            >
              <span className="auth-demo-divider"><span>or</span></span>
              <button type="button" className="auth-demo-button" onClick={onExploreDemo}>
                <Sparkles size={16} />
                Explore in demo mode
                <ArrowRight size={15} />
              </button>
              <p>Continue without an account. Demo uses sample data; changes are not saved.</p>
            </motion.div>
          )}

          <motion.div
            className="auth-secure-note"
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.68 }}
          >
            <ShieldCheck size={15} /> Your password is never saved by NutriAI.
          </motion.div>
        </section>
      </motion.section>
      <p className="auth-footer">NOURISH YOURSELF, ONE GOOD CHOICE AT A TIME</p>
    </main>
  );
}
