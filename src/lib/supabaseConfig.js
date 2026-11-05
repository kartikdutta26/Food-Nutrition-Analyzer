export const SUPABASE_AUTH_OPTIONS = Object.freeze({
  flowType: 'implicit',
  detectSessionInUrl: true,
  persistSession: true,
  autoRefreshToken: true,
});

export function getSupabaseConfig(env = {}) {
  const url = typeof env.VITE_SUPABASE_URL === 'string'
    ? env.VITE_SUPABASE_URL.trim()
    : '';
  const publishableKey = typeof env.VITE_SUPABASE_PUBLISHABLE_KEY === 'string'
    ? env.VITE_SUPABASE_PUBLISHABLE_KEY.trim()
    : '';

  const missingVariables = [];
  if (!url) missingVariables.push('VITE_SUPABASE_URL');
  if (!publishableKey) missingVariables.push('VITE_SUPABASE_PUBLISHABLE_KEY');

  if (missingVariables.length > 0) {
    throw new Error(
      `Missing required Supabase environment variable(s): ${missingVariables.join(', ')}`,
    );
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch {
    throw new Error('VITE_SUPABASE_URL must be a valid HTTP(S) URL.');
  }

  if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
    throw new Error('VITE_SUPABASE_URL must be a valid HTTP(S) URL.');
  }

  const configuredPath = parsedUrl.pathname.replace(/\/+$/, '');
  if (
    (configuredPath && configuredPath !== '/rest/v1')
    || parsedUrl.username
    || parsedUrl.password
    || parsedUrl.search
    || parsedUrl.hash
  ) {
    throw new Error('VITE_SUPABASE_URL must be the project URL, not a nested service endpoint.');
  }

  // Supabase clients need the project root to build /auth/v1, /rest/v1, and
  // storage URLs. Accept the REST endpoint copied from the API settings, but
  // normalize it before any Auth or Data client is created.
  return { url: parsedUrl.origin, publishableKey };
}
