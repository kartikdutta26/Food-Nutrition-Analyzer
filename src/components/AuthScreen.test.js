import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { getRegistrationSuccessMessage } from '../lib/authFlows.js';

test('authentication screens expose labeled fields, verification messaging, and reset states', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: AuthScreen } = await vite.ssrLoadModule('/src/components/AuthScreen.jsx');
    const baseProps = {
      onModeChange: () => {},
      onRegister: async () => ({ needsEmailVerification: true }),
      onLogin: async () => {},
      onResendVerification: async () => {},
      onConfirmEmail: async () => ({ verified: true, authenticated: false }),
      onForgotPassword: async () => {},
      onResetPassword: async () => {},
      onAuthenticated: () => {},
      onPasswordResetComplete: () => {},
      onExploreFood: () => {},
    };
    const render = (props) => renderToStaticMarkup(createElement(AuthScreen, { ...baseProps, ...props }));

    const signup = render({ mode: 'signup' });
    assert.match(signup, /Create your account/);
    assert.match(signup, /for="auth-name"[^>]*>Name/);
    assert.match(signup, /for="auth-email"[^>]*>Email address/);
    assert.match(signup, /for="auth-password"[^>]*>Password/);
    assert.match(signup, /for="auth-confirm-password"[^>]*>Confirm password/);
    assert.match(signup, /verification link to your email/);
    assert.match(signup, /localhost link works only on the computer running Vite/);
    assert.match(signup, /type="email"/);
    assert.equal(
      getRegistrationSuccessMessage('casey@example.com', { needsEmailVerification: true }),
      'Registration submitted for casey@example.com. If this is a new account, Supabase accepted a confirmation-email request. Check your inbox and spam folder, then confirm your address before signing in.',
    );

    const login = render({ mode: 'login' });
    assert.match(login, /Sign in to NutriAI/);
    assert.match(login, /Forgot password\?/);
    assert.match(login, /Create an account/);
    assert.match(login, /Resend confirmation email/);

    const verify = render({ mode: 'verify' });
    assert.match(verify, /Confirm your email/);
    assert.match(verify, /Supabase will verify it only after you press the button/);
    assert.match(verify, /Confirm email/);
    assert.doesNotMatch(verify, /opaque-confirmation-value/);

    const forgot = render({ mode: 'forgot' });
    assert.match(forgot, /Send reset email/);
    assert.match(forgot, /Back to sign in/);
    assert.match(forgot, /Enter your account email/);

    const reset = render({ mode: 'reset', recoveryReady: true });
    assert.match(reset, /Finish password reset/);
    assert.match(reset, /for="auth-password"[^>]*>New password/);
    assert.match(reset, /for="auth-confirm-password"[^>]*>Confirm password/);

    const pendingReset = render({ mode: 'reset', recoveryReady: false });
    assert.match(pendingReset, /Checking your secure password reset link/);
    assert.doesNotMatch(pendingReset, /id="auth-password"/);
  } finally {
    await vite.close();
  }
});
