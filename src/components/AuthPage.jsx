import { useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  BrainCircuit,
  ChartNoAxesCombined,
  Eye,
  EyeOff,
  Goal,
  Leaf,
  LockKeyhole,
  Mail,
  Salad,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react';
import './auth.css';

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const passwordRequirement = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

export default function AuthPage({ onAuthenticate, onResetPassword, onExploreDemo, onOpenAdvancedAuth, authConfigured }) {
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
      if (mode === 'signup' && result?.type === 'success') {
        setPassword('');
        setConfirmPassword('');
        setMode('login');
      }
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
      <div className="auth-atmosphere" aria-hidden="true">
        <div className="auth-glow auth-glow--mint" />
        <div className="auth-glow auth-glow--peach" />
        <div className="auth-glow auth-glow--lilac" />
        <div className="auth-ribbon auth-ribbon--back" />
        <div className="auth-ribbon auth-ribbon--front" />
        <div className="auth-orb auth-orb--one" />
        <div className="auth-orb auth-orb--two" />
        <div className="auth-orb auth-orb--three" />
        <div className="auth-leaf auth-leaf--one"><Leaf size={52} strokeWidth={1} /></div>
        <div className="auth-leaf auth-leaf--two"><Leaf size={36} strokeWidth={1} /></div>
        <div className="auth-grain" />
      </div>

      <motion.section
        className="auth-card"
        initial={reducedMotion ? false : { opacity: 0, y: 22, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
        aria-label="NutriAI account access"
      >
        <section className="auth-story" aria-labelledby="auth-headline">
          <div className="auth-brand">
            <span className="auth-brand-mark"><Salad size={23} strokeWidth={1.8} /></span>
            <span className="auth-brand-word">Nutri<span>AI</span><small>INTELLIGENT NUTRITION</small></span>
          </div>

          <div className="auth-story-copy">
            <span className="auth-eyebrow"><Sparkles size={14} /> A little more in tune</span>
            <h1 id="auth-headline">Your food.<br />Your goals.<br /><span>A healthier you.</span></h1>
            <p>Snap your meals, get personalized nutrition insights, and build healthier habits with the power of AI.</p>
            <div className="auth-benefits" aria-label="NutriAI benefits">
              <span><i><BrainCircuit size={16} /></i><span>AI-powered food insights</span></span>
              <span><i><Goal size={16} /></i><span>Personalized nutrition goals</span></span>
              <span><i><ChartNoAxesCombined size={16} /></i><span>Smart meal tracking</span></span>
            </div>
          </div>

          <div className="auth-food-art">
            <span className="auth-food-orbit auth-food-orbit--one" aria-hidden="true" />
            <span className="auth-food-orbit auth-food-orbit--two" aria-hidden="true" />
            <span className="auth-food-sparkle auth-food-sparkle--one" aria-hidden="true"><Sparkles size={18} /></span>
            <span className="auth-food-sparkle auth-food-sparkle--two" aria-hidden="true"><Sparkles size={13} /></span>
            <img src="/nutriai-3d-meal-bowl.png" alt="A vibrant bowl of greens, avocado, tomatoes, grains, and chickpeas" />
            <div className="auth-food-caption">
              <span className="auth-food-caption-icon"><Leaf size={15} /></span>
              <span><strong>Real food. Smarter choices.</strong><small>Your nutrition, made personal</small></span>
              <span className="auth-food-spark"><Sparkles size={17} /></span>
            </div>
          </div>
          <span className="auth-story-note"><ShieldCheck size={14} /> Your wellness journey, your way</span>
        </section>

        <section className="auth-form-panel" aria-label={isSignup ? 'Create your account' : 'Sign in to your account'}>
          <div className="auth-mobile-brand">
            <span className="auth-brand-mark"><Salad size={21} /></span>
            <span className="auth-brand-word">Nutri<span>AI</span></span>
          </div>
          <div className="auth-form-heading">
            <span className="auth-form-kicker">WELCOME TO YOUR WELLNESS SPACE</span>
            <h2>{isSignup ? 'Create your account' : 'Welcome back'}</h2>
            <p>{isSignup ? 'A healthier routine starts with a simple step.' : 'Your next healthy choice starts right here.'}</p>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Choose login or sign up">
            <button type="button" role="tab" aria-selected={!isSignup} className={!isSignup ? 'is-selected' : ''} onClick={() => changeMode('login')}>Login</button>
            <button type="button" role="tab" aria-selected={isSignup} className={isSignup ? 'is-selected' : ''} onClick={() => changeMode('signup')}>Sign Up</button>
          </div>

          <div className="auth-setup-note" role="status">
            <span className="auth-setup-dot" />
            {authConfigured ? 'Secure sign-in powered by Supabase.' : 'Add your Supabase project settings to enable accounts.'}
          </div>

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
                <label className="auth-field">
                  <span>Full name</span>
                  <span className="auth-input-wrap">
                    <UserRound size={17} aria-hidden="true" />
                    <input autoComplete="name" name="name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="How should we call you?" />
                  </span>
                </label>
              )}
              <label className="auth-field">
                <span>Email address</span>
                <span className="auth-input-wrap">
                  <Mail size={17} aria-hidden="true" />
                  <input autoComplete="email" name="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" />
                </span>
              </label>
              <label className="auth-field">
                <span>Password</span>
                <span className="auth-input-wrap">
                  <LockKeyhole size={17} aria-hidden="true" />
                  <input autoComplete={isSignup ? 'new-password' : 'current-password'} name="password" type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isSignup ? 'Create a strong password' : 'Enter your password'} />
                  <button className="auth-password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </span>
                {isSignup && <small className="auth-hint">8+ characters with uppercase, lowercase, and a number.</small>}
              </label>
              {isSignup && (
                <label className="auth-field">
                  <span>Confirm password</span>
                  <span className="auth-input-wrap">
                    <LockKeyhole size={17} aria-hidden="true" />
                    <input autoComplete="new-password" name="confirm-password" type={showPassword ? 'text' : 'password'} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" />
                  </span>
                </label>
              )}

              {!isSignup && (
                <div className="auth-forgot-row">
                  <span>Forgot your password?</span>
                  <button type="button" onClick={handleForgotPassword} disabled={isSubmitting}>Reset it</button>
                </div>
              )}

              {feedback && (
                <div className={`auth-feedback auth-feedback--${feedback.type}`} role={feedback.type === 'error' ? 'alert' : 'status'}>
                  {feedback.message}
                </div>
              )}

              <button className="auth-submit" type="submit" disabled={isSubmitting}>
                {isSubmitting ? <span className="auth-spinner" aria-hidden="true" /> : <>{isSignup ? 'Create account' : 'Login'} <ArrowRight size={17} /></>}
                <span className="sr-only">{isSubmitting ? 'Please wait' : ''}</span>
              </button>
              <p className="auth-terms">A healthier routine starts with choices that work for you.</p>
            </motion.form>
          </AnimatePresence>

          {onExploreDemo && (
            <div className="auth-demo-entry">
              <span className="auth-demo-divider"><span>or</span></span>
              <button type="button" className="auth-demo-button" onClick={onExploreDemo}>
                <Sparkles size={16} />
                Explore in demo mode
                <ArrowRight size={15} />
              </button>
              <p>Continue without an account. Demo uses sample data; changes are not saved.</p>
            </div>
          )}

          <div className="auth-secure-note"><ShieldCheck size={15} /> Your password is never saved by NutriAI.</div>
          {onOpenAdvancedAuth && (
            <div className="auth-forgot-row mt-3">
              <span>Need email verification or account recovery?</span>
              <button type="button" onClick={onOpenAdvancedAuth}>Open account help</button>
            </div>
          )}
        </section>
      </motion.section>
      <p className="auth-footer">NOURISH YOURSELF, ONE GOOD CHOICE AT A TIME</p>
    </main>
  );
}
