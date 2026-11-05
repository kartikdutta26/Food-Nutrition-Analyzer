const AUTH_REDIRECT_FLOWS = new Set(['verify', 'recovery']);
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]', '::1']);
const EMAIL_OTP_TYPES = new Set(['email', 'signup']);

function isPrivateLanIPv4(hostname) {
  const parts = hostname.split('.');
  if (parts.length !== 4 || parts.some((part) => !/^\d{1,3}$/.test(part))) return false;
  const octets = parts.map(Number);
  if (octets.some((octet) => octet < 0 || octet > 255)) return false;
  return octets[0] === 10
    || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168);
}

export class EmailVerificationRequiredError extends Error {
  constructor() {
    super('Verify your email address before signing in.');
    this.name = 'EmailVerificationRequiredError';
  }
}

export function resolveAuthRedirectOrigin({
  publicAppUrl = '',
  isDevelopment = false,
} = {}) {
  const configured = typeof publicAppUrl === 'string' ? publicAppUrl.trim() : '';
  if (!configured) {
    throw new Error('Set VITE_APP_PUBLIC_URL to the exact application origin allowlisted in Supabase before using email links.');
  }

  let parsed;
  try {
    parsed = new URL(configured);
  } catch {
    throw new Error('The configured NutriAI application origin must be a valid URL.');
  }

  const isLocal = LOCAL_HOSTS.has(parsed.hostname);
  const isPrivateLan = isPrivateLanIPv4(parsed.hostname);
  if (
    !['http:', 'https:'].includes(parsed.protocol)
    || (parsed.protocol !== 'https:' && !(isDevelopment && (isLocal || isPrivateLan)))
    || (isLocal && !isDevelopment)
    || (isPrivateLan && !isDevelopment && parsed.protocol !== 'https:')
  ) {
    throw new Error('Use HTTPS, except for an explicitly configured localhost or private-LAN development origin.');
  }
  if (
    parsed.username
    || parsed.password
    || (parsed.pathname !== '' && parsed.pathname !== '/')
    || parsed.search
    || parsed.hash
  ) {
    throw new Error('The configured NutriAI application origin must not include a path or query.');
  }

  return parsed.origin;
}

export function buildAuthRedirectUrl(flow, redirectOptions = {}) {
  if (!AUTH_REDIRECT_FLOWS.has(flow)) {
    throw new Error('Unsupported authentication redirect flow.');
  }

  const origin = resolveAuthRedirectOrigin(redirectOptions);
  const redirectUrl = new URL('/', origin);
  redirectUrl.searchParams.set('auth', flow);
  return redirectUrl.toString();
}

function parseUrl(href) {
  try {
    return new URL(href);
  } catch {
    return null;
  }
}

function callbackParams(url) {
  const params = new URLSearchParams(url.hash.replace(/^#/, ''));
  url.searchParams.forEach((value, key) => {
    if (!params.has(key)) params.set(key, value);
  });
  return params;
}

export function getAuthRedirectInfo(href) {
  const url = parseUrl(href);
  if (!url) return { flow: null, error: null };

  const params = callbackParams(url);
  const requestedFlow = url.searchParams.get('auth');
  const callbackType = params.get('type');
  const flow = AUTH_REDIRECT_FLOWS.has(requestedFlow)
    ? requestedFlow
    : callbackType === 'recovery'
      ? 'recovery'
      : callbackType === 'signup' || callbackType === 'email'
        ? 'verify'
        : null;
  const hasRedirectError = ['error', 'error_code', 'error_description']
    .some((key) => params.has(key));

  if (!hasRedirectError) return { flow, error: null };

  const code = params.get('error_code') || params.get('error') || '';
  const description = params.get('error_description') || '';
  const isExpiredOrConsumed = /expired|invalid|otp|already.?used/i.test(`${code} ${description}`);
  const error = isExpiredOrConsumed
    ? flow === 'recovery'
      ? 'This password reset link is invalid, expired, or already used. Request a fresh reset email and open its latest link.'
      : 'This confirmation link is invalid, expired, or already used. Request a fresh email and complete confirmation from the page it opens.'
    : 'Supabase could not complete this email link. Sign in if your email is confirmed, or request a fresh link.';

  return { flow, error };
}

export function getEmailConfirmationCallback(href) {
  const url = parseUrl(href);
  if (!url) return null;
  const params = callbackParams(url);
  const tokenHash = params.get('token_hash');
  const type = params.get('type');
  if (!tokenHash || !EMAIL_OTP_TYPES.has(type)) return null;
  return { tokenHash, type };
}

export function hasSupabaseAuthCallbackPayload(href) {
  const url = parseUrl(href);
  if (!url) return false;
  const params = callbackParams(url);
  return ['code', 'access_token', 'refresh_token', 'token_hash'].some((key) => params.has(key));
}

export function cleanAuthRedirectUrl(href) {
  const url = parseUrl(href);
  if (!url) return '/';
  [
    'auth', 'code', 'error', 'error_code', 'error_description', 'type', 'token_hash',
    'access_token', 'refresh_token', 'expires_in', 'expires_at', 'provider_token',
    'provider_refresh_token', 'token_type', 'sb_flow_id',
  ].forEach((key) => url.searchParams.delete(key));
  url.hash = '';
  return `${url.pathname}${url.search}`;
}

export function cleanEmailConfirmationTokenFromUrl(href) {
  const url = parseUrl(href);
  if (!url) return '/';
  ['token_hash', 'type'].forEach((key) => url.searchParams.delete(key));
  const hash = new URLSearchParams(url.hash.replace(/^#/, ''));
  hash.delete('token_hash');
  hash.delete('type');
  const remainingHash = hash.toString();
  url.hash = remainingHash ? `#${remainingHash}` : '';
  return `${url.pathname}${url.search}${url.hash}`;
}

export function isEmailVerified(user) {
  return Boolean(user?.email_confirmed_at);
}

export function getVerifiedUser(session) {
  const user = session?.user;
  return isEmailVerified(user) ? user : null;
}

export function getRegistrationSuccessMessage(email, result) {
  if (result?.duplicate) {
    return `Registration submitted. If an account exists for ${email}, sign in or request a password reset. Otherwise, check your inbox for a confirmation email.`;
  }
  if (result?.needsEmailVerification) {
    const status = result.user?.id
      ? `Account created for ${email}. Supabase accepted a request to send a confirmation email.`
      : `Registration submitted for ${email}. If this is a new account, Supabase accepted a confirmation-email request.`;
    return `${status} Check your inbox and spam folder, then confirm your address before signing in.`;
  }
  return 'Your account is confirmed and ready. Sign in to continue.';
}

export async function registerWithEmail(client, { name, email, password }, redirectOptions) {
  const { data, error } = await client.auth.signUp({
    email: email.trim().toLowerCase(),
    password,
    options: {
      data: { full_name: name.trim() },
      emailRedirectTo: buildAuthRedirectUrl('verify', redirectOptions),
    },
  });

  if (error) throw error;

  const user = data?.user ?? null;
  const session = data?.session ?? null;
  const duplicate = Array.isArray(user?.identities) && user.identities.length === 0;
  const verified = isEmailVerified(user);

  if (duplicate || (session && !verified)) {
    try {
      await client.auth.signOut({ scope: 'local' });
    } catch {
      // UI and backend verification still prevent unverified access.
    }
  }

  return {
    user: duplicate ? null : user,
    session: !duplicate && verified ? session : null,
    duplicate,
    needsEmailVerification: !duplicate && !verified,
    authenticated: Boolean(!duplicate && session && verified),
  };
}

export async function verifyEmailWithTokenHash(client, { tokenHash, type = 'email' } = {}) {
  if (typeof tokenHash !== 'string' || !tokenHash || !EMAIL_OTP_TYPES.has(type)) {
    throw new Error('This confirmation link is not valid. Request a fresh confirmation email.');
  }

  const { data, error } = await client.auth.verifyOtp({ token_hash: tokenHash, type });
  if (error) throw error;

  const user = data?.user ?? data?.session?.user ?? null;
  const verified = isEmailVerified(user);
  if (!verified) {
    throw new Error('Supabase did not confirm this email address. Sign in or request a fresh link.');
  }

  return {
    user,
    session: data?.session ?? null,
    verified,
    authenticated: Boolean(data?.session && verified),
  };
}

export function createIdempotentCallbackProcessor() {
  let callbackPromise = null;
  return (callback) => {
    if (!callbackPromise) callbackPromise = Promise.resolve().then(callback);
    return callbackPromise;
  };
}

export async function resendSignupVerification(client, email, redirectOptions) {
  const normalizedEmail = email.trim().toLowerCase();
  const { error } = await client.auth.resend({
    type: 'signup',
    email: normalizedEmail,
    options: { emailRedirectTo: buildAuthRedirectUrl('verify', redirectOptions) },
  });
  if (error) throw error;
}

export async function loginWithEmail(client, { email, password }) {
  const { data, error } = await client.auth.signInWithPassword({
    email: email.trim().toLowerCase(),
    password,
  });

  if (error) throw error;

  const user = data?.user ?? data?.session?.user ?? null;
  if (!isEmailVerified(user)) {
    try {
      await client.auth.signOut({ scope: 'local' });
    } catch {
      // The UI still rejects this account even if local session cleanup fails.
    }
    throw new EmailVerificationRequiredError();
  }

  return { user, session: data?.session ?? null };
}

export async function sendPasswordReset(client, email, redirectOptions) {
  const { error } = await client.auth.resetPasswordForEmail(
    email.trim().toLowerCase(),
    { redirectTo: buildAuthRedirectUrl('recovery', redirectOptions) },
  );

  if (error) throw error;
}

export async function updatePassword(client, password) {
  const { data, error } = await client.auth.updateUser({ password });
  if (error) throw error;
  return data;
}

export async function signOutLocally(client) {
  const { error } = await client.auth.signOut({ scope: 'local' });
  if (error) throw error;
}

export function subscribeToVerifiedAuthState(client, {
  onUser,
  onPasswordRecovery,
  onInitialSession,
} = {}) {
  const { data } = client.auth.onAuthStateChange((event, session) => {
    const user = getVerifiedUser(session);
    onUser?.(user, event);

    if (event === 'PASSWORD_RECOVERY') onPasswordRecovery?.(user);
    if (event === 'INITIAL_SESSION') onInitialSession?.(user);
  });

  return () => data?.subscription?.unsubscribe?.();
}

export function friendlyAuthError(error, action) {
  const errorCode = String(error?.code || '').toLowerCase();
  const message = String(error?.message || '').toLowerCase();

  if (
    error?.name === 'EmailVerificationRequiredError'
    || errorCode === 'email_not_confirmed'
    || /email not confirmed|email_not_confirmed/.test(message)
  ) {
    return 'Please verify your email address using the link we sent before signing in.';
  }

  if (message.includes('vite_app_public_url')) {
    return 'Set VITE_APP_PUBLIC_URL to the exact app origin allowlisted in Supabase. Localhost only works on this machine; use a reachable LAN or deployed origin for another device.';
  }
  const expiredLinkError = /otp[_\s-]+(?:not[_\s-]+found|expired)|(?:token|link)[\s\S]*(?:expired|invalid)|(?:expired|invalid)[\s\S]*(?:token|link)|already[\s_-]*used/i
    .test(`${errorCode} ${message}`);
  if (expiredLinkError) {
    return action === 'reset'
      ? 'This password reset link is invalid, expired, or already used. Request a fresh reset email.'
      : 'This confirmation link may have expired or been opened automatically. Request a fresh confirmation email and complete confirmation from the page it opens.';
  }
  if (message.includes('rate limit') || message.includes('too many requests')) {
    return 'Too many attempts. Please wait a little and try again.';
  }
  if (message.includes('password') && /weak|length|characters|short/.test(message)) {
    return 'Choose a longer password and try again.';
  }

  if (action === 'login') {
    return 'Email or password was incorrect. If you have not verified your email, check your inbox.';
  }
  if (action === 'signup') return 'We could not submit your registration. Check the form and try again.';
  if (action === 'resend') return 'We could not request another confirmation email. Please try again shortly.';
  if (action === 'verify') return 'We could not confirm this email address. Sign in if already confirmed, or request a fresh link.';
  if (action === 'forgot') return 'We could not send a reset email right now. Please try again.';
  if (action === 'reset') return 'We could not update your password. Check the reset link and try again.';
  return 'Something went wrong. Please try again.';
}
