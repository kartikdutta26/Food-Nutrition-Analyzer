import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim();
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();

export const authConfigured = Boolean(supabaseUrl && supabaseAnonKey);

if (Boolean(supabaseUrl) !== Boolean(supabaseAnonKey)) {
  console.error('Supabase authentication requires both VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
}

export const authClient = authConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })
  : null;
