import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildAuthRedirectUrl,
  cleanAuthRedirectUrl,
  cleanEmailConfirmationTokenFromUrl,
  createIdempotentCallbackProcessor,
  EmailVerificationRequiredError,
  friendlyAuthError,
  getAuthRedirectInfo,
  getEmailConfirmationCallback,
  getRegistrationSuccessMessage,
  getVerifiedUser,
  hasSupabaseAuthCallbackPayload,
  isEmailVerified,
  loginWithEmail,
  registerWithEmail,
  resendSignupVerification,
  resolveAuthRedirectOrigin,
  sendPasswordReset,
  signOutLocally,
  subscribeToVerifiedAuthState,
  updatePassword,
  verifyEmailWithTokenHash,
} from './authFlows.js';

const devRedirect = {
  publicAppUrl: 'http://localhost:5173',
  isDevelopment: true,
};

test('registration requests confirmation at the explicitly configured local callback and stores the name as metadata', async () => {
  let request;
  const client = {
    auth: {
      signUp: async (input) => {
        request = input;
        return {
          data: { user: { id: 'user-1', email_confirmed_at: null }, session: null },
          error: null,
        };
      },
    },
  };

  const result = await registerWithEmail(client, {
    name: '  Casey Rivera ',
    email: ' Casey@example.com ',
    password: 'example-password',
  }, devRedirect);

  assert.deepEqual(request, {
    email: 'casey@example.com',
    password: 'example-password',
    options: {
      data: { full_name: 'Casey Rivera' },
      emailRedirectTo: 'http://localhost:5173/?auth=verify',
    },
  });
  assert.equal(result.needsEmailVerification, true);
  assert.equal(result.authenticated, false);
  assert.match(getRegistrationSuccessMessage('casey@example.com', result), /Account created.*confirmation email/);
});

test('duplicate registration is not reported as a newly created account or authenticated session', async () => {
  let signOutScope;
  const client = {
    auth: {
      signUp: async () => ({
        data: {
          user: { id: 'existing-user', identities: [], email_confirmed_at: '2026-10-01T00:00:00Z' },
          session: { access_token: 'not-retained', user: { id: 'existing-user' } },
        },
        error: null,
      }),
      signOut: async (options) => {
        signOutScope = options.scope;
        return { error: null };
      },
    },
  };

  const result = await registerWithEmail(client, {
    name: 'Casey Rivera',
    email: 'casey@example.com',
    password: 'example-password',
  }, devRedirect);

  assert.equal(result.duplicate, true);
  assert.equal(result.authenticated, false);
  assert.equal(result.needsEmailVerification, false);
  assert.equal(signOutScope, 'local');
  assert.match(getRegistrationSuccessMessage('casey@example.com', result), /If an account exists/);
  assert.doesNotMatch(getRegistrationSuccessMessage('casey@example.com', result), /confirmed successfully/i);
});

test('verification links are built from an explicit production origin, not the local browser origin', () => {
  const productionRedirect = {
    publicAppUrl: 'https://nutriai.example.com',
    isDevelopment: false,
  };

  assert.equal(resolveAuthRedirectOrigin(productionRedirect), 'https://nutriai.example.com');
  assert.equal(buildAuthRedirectUrl('verify', productionRedirect), 'https://nutriai.example.com/?auth=verify');
  assert.equal(buildAuthRedirectUrl('recovery', productionRedirect), 'https://nutriai.example.com/?auth=recovery');
  assert.equal(buildAuthRedirectUrl('verify', devRedirect), 'http://localhost:5173/?auth=verify');
});

test('production redirects fail closed without an explicit HTTPS origin or with a URL path', () => {
  assert.throws(
    () => resolveAuthRedirectOrigin({ isDevelopment: false }),
    /VITE_APP_PUBLIC_URL/,
  );
  assert.throws(
    () => resolveAuthRedirectOrigin({ publicAppUrl: 'http://localhost:5173', isDevelopment: false }),
    /HTTPS/,
  );
  assert.throws(
    () => resolveAuthRedirectOrigin({ publicAppUrl: 'http://nutriai.example.com', isDevelopment: false }),
    /HTTPS/,
  );
  assert.throws(
    () => resolveAuthRedirectOrigin({ publicAppUrl: 'https://nutriai.example.com/auth/callback', isDevelopment: false }),
    /application origin/,
  );
});

test('email redirects require an explicit allowlisted origin and support configured LAN development origins', () => {
  assert.throws(
    () => resolveAuthRedirectOrigin({ currentOrigin: 'http://localhost:5173', isDevelopment: true }),
    /VITE_APP_PUBLIC_URL/,
  );
  assert.equal(
    resolveAuthRedirectOrigin({ publicAppUrl: 'http://192.168.1.25:5173', isDevelopment: true }),
    'http://192.168.1.25:5173',
  );
  assert.throws(
    () => resolveAuthRedirectOrigin({ publicAppUrl: 'http://example.com', isDevelopment: true }),
    /HTTPS/,
  );
  assert.throws(
    () => resolveAuthRedirectOrigin({ publicAppUrl: 'http://192.168.1.25:5173', isDevelopment: false }),
    /HTTPS/,
  );
});

test('confirmation callbacks extract a token hash without displaying or retaining it in the cleaned URL', () => {
  const callback = getEmailConfirmationCallback(
    'https://nutriai.example.com/?auth=verify&token_hash=opaque-confirmation-value&type=email',
  );
  assert.deepEqual(callback, { tokenHash: 'opaque-confirmation-value', type: 'email' });
  assert.equal(
    cleanEmailConfirmationTokenFromUrl('https://nutriai.example.com/?auth=verify&token_hash=opaque-confirmation-value&type=email'),
    '/?auth=verify',
  );
  assert.equal(hasSupabaseAuthCallbackPayload('https://nutriai.example.com/?auth=verify&token_hash=x&type=email'), true);
});

test('confirmation is explicitly verified through Supabase and requires a confirmed user', async () => {
  let request;
  const confirmedUser = { id: 'user-verified', email_confirmed_at: '2026-10-01T00:00:00Z' };
  const client = {
    auth: {
      verifyOtp: async (input) => {
        request = input;
        return { data: { user: confirmedUser, session: { user: confirmedUser } }, error: null };
      },
    },
  };

  const result = await verifyEmailWithTokenHash(client, { tokenHash: 'opaque-value', type: 'email' });
  assert.deepEqual(request, { token_hash: 'opaque-value', type: 'email' });
  assert.equal(result.verified, true);
  assert.equal(result.authenticated, true);

  const unverifiedClient = {
    auth: {
      verifyOtp: async () => ({ data: { user: { id: 'user-unverified' }, session: null }, error: null }),
    },
  };
  await assert.rejects(
    verifyEmailWithTokenHash(unverifiedClient, { tokenHash: 'opaque-value' }),
    /did not confirm/,
  );
});

test('one callback processor shares the same promise and invokes a consumed callback only once', async () => {
  const processOnce = createIdempotentCallbackProcessor();
  let calls = 0;
  let finish;
  const callback = () => {
    calls += 1;
    return new Promise((resolve) => { finish = resolve; });
  };

  const first = processOnce(callback);
  const second = processOnce(callback);
  assert.equal(first, second);
  await Promise.resolve();
  assert.equal(calls, 1);
  finish({ success: true });
  assert.deepEqual(await first, { success: true });
});

test('invalid and already-consumed callback responses are recognized without exposing callback values', () => {
  const info = getAuthRedirectInfo(
    'https://nutriai.example.com/?auth=verify#error_code=otp_expired&error_description=opaque-detail',
  );
  assert.equal(info.flow, 'verify');
  assert.match(info.error, /invalid, expired, or already used/);
  assert.doesNotMatch(info.error, /opaque-detail|otp_expired/);
  assert.equal(
    hasSupabaseAuthCallbackPayload('https://nutriai.example.com/?auth=verify&code=one-time-code'),
    true,
  );
});

test('callback errors distinguish expired confirmation links from expired password reset links', () => {
  const confirmation = getAuthRedirectInfo(
    'https://nutriai.example.com/?auth=verify#error_code=otp_expired&error_description=opaque-detail',
  );
  const recovery = getAuthRedirectInfo(
    'https://nutriai.example.com/?auth=recovery#error_code=otp_expired&error_description=opaque-detail',
  );

  assert.match(confirmation.error, /confirmation link is invalid, expired, or already used/);
  assert.match(recovery.error, /password reset link is invalid, expired, or already used/);
  assert.doesNotMatch(`${confirmation.error} ${recovery.error}`, /opaque-detail|otp_expired/);
});

test('standard implicit confirmation callbacks are recognized but a marker alone is not a callback proof', () => {
  const standardCallback = 'https://nutriai.example.com/?auth=verify#access_token=fake-access&refresh_token=fake-refresh&expires_in=3600&token_type=bearer&type=signup';
  assert.deepEqual(getAuthRedirectInfo(standardCallback), { flow: 'verify', error: null });
  assert.equal(hasSupabaseAuthCallbackPayload(standardCallback), true);
  assert.equal(getAuthRedirectInfo('https://nutriai.example.com/?auth=verify').flow, 'verify');
  assert.equal(hasSupabaseAuthCallbackPayload('https://nutriai.example.com/?auth=verify'), false);
  assert.equal(
    getEmailConfirmationCallback('https://nutriai.example.com/?auth=verify&token_hash=opaque&type=unsupported'),
    null,
  );
});

test('verified login uses signInWithPassword and returns the signed-in user', async () => {
  let request;
  const user = { id: 'user-2', email_confirmed_at: '2026-10-01T00:00:00Z' };
  const client = {
    auth: {
      signInWithPassword: async (input) => {
        request = input;
        return { data: { user, session: { user } }, error: null };
      },
    },
  };

  const result = await loginWithEmail(client, { email: ' USER@example.com ', password: 'correct-password' });
  assert.deepEqual(request, { email: 'user@example.com', password: 'correct-password' });
  assert.equal(result.user, user);
});

test('login failures and unverified accounts cannot become authenticated', async () => {
  const loginError = new Error('Invalid login credentials');
  const failingClient = { auth: { signInWithPassword: async () => ({ data: null, error: loginError }) } };
  await assert.rejects(loginWithEmail(failingClient, { email: 'casey@example.com', password: 'wrong' }), loginError);

  let signOutScope;
  const unverifiedClient = {
    auth: {
      signInWithPassword: async () => ({
        data: { user: { id: 'unverified-user', email_confirmed_at: null }, session: { user: { id: 'unverified-user' } } },
        error: null,
      }),
      signOut: async (options) => {
        signOutScope = options.scope;
        return { error: null };
      },
    },
  };

  await assert.rejects(
    loginWithEmail(unverifiedClient, { email: 'casey@example.com', password: 'example-password' }),
    EmailVerificationRequiredError,
  );
  assert.equal(signOutScope, 'local');
});

test('Supabase unconfirmed-email login errors show verification guidance, not invalid credentials', () => {
  const error = Object.assign(new Error('Email not confirmed'), { code: 'email_not_confirmed' });
  const verificationMessage = friendlyAuthError(error, 'login');
  const credentialsMessage = friendlyAuthError(new Error('Invalid login credentials'), 'login');

  assert.match(verificationMessage, /verify your email address/i);
  assert.doesNotMatch(verificationMessage, /incorrect/i);
  assert.match(credentialsMessage, /email or password was incorrect/i);
});

test('session restoration exposes only verified users and unsubscribes cleanly', () => {
  let listener;
  let unsubscribed = false;
  const userEvents = [];
  const recoveryEvents = [];
  const initialEvents = [];
  const client = {
    auth: {
      onAuthStateChange: (callback) => {
        listener = callback;
        return { data: { subscription: { unsubscribe: () => { unsubscribed = true; } } } };
      },
    },
  };

  const unsubscribe = subscribeToVerifiedAuthState(client, {
    onUser: (user, event) => userEvents.push({ user, event }),
    onPasswordRecovery: (user) => recoveryEvents.push(user),
    onInitialSession: (user) => initialEvents.push(user),
  });

  const verifiedUser = { id: 'restored-user', email_confirmed_at: '2026-10-01T00:00:00Z' };
  listener('INITIAL_SESSION', { user: verifiedUser });
  listener('PASSWORD_RECOVERY', { user: verifiedUser });
  listener('SIGNED_IN', { user: { id: 'unverified-user', email_confirmed_at: null } });

  assert.equal(initialEvents[0], verifiedUser);
  assert.equal(recoveryEvents[0], verifiedUser);
  assert.equal(userEvents[2].user, null);
  assert.equal(isEmailVerified({ email_confirmed_at: null }), false);
  assert.equal(getVerifiedUser({ user: verifiedUser }), verifiedUser);
  unsubscribe();
  assert.equal(unsubscribed, true);
});

test('resend, password recovery, password reset, and local logout use supported Supabase methods', async () => {
  const requests = [];
  const client = {
    auth: {
      resend: async (input) => { requests.push(['resend', input]); return { error: null }; },
      resetPasswordForEmail: async (...args) => { requests.push(['reset', ...args]); return { error: null }; },
      updateUser: async (input) => { requests.push(['update', input]); return { data: { user: { id: 'user-3' } }, error: null }; },
      signOut: async (input) => { requests.push(['logout', input]); return { error: null }; },
    },
  };

  await resendSignupVerification(client, ' CASEY@example.com ', devRedirect);
  await sendPasswordReset(client, ' CASEY@example.com ', devRedirect);
  const result = await updatePassword(client, 'a-new-strong-password');
  await signOutLocally(client);

  assert.deepEqual(requests[0], ['resend', {
    type: 'signup',
    email: 'casey@example.com',
    options: { emailRedirectTo: 'http://localhost:5173/?auth=verify' },
  }]);
  assert.deepEqual(requests[1], ['reset', 'casey@example.com', { redirectTo: 'http://localhost:5173/?auth=recovery' }]);
  assert.deepEqual(requests[2], ['update', { password: 'a-new-strong-password' }]);
  assert.deepEqual(requests[3], ['logout', { scope: 'local' }]);
  assert.equal(result.user.id, 'user-3');
});

test('callback cleanup removes sensitive values while preserving unrelated query parameters', () => {
  assert.equal(
    cleanAuthRedirectUrl('https://nutriai.example.com/?auth=verify&keep=1&code=discard&access_token=discard#refresh_token=discard'),
    '/?keep=1',
  );
});
