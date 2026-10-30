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

  return { url, publishableKey };
}
