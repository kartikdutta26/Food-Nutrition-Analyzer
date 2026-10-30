import { createClient } from '@supabase/supabase-js';
import { getSupabaseConfig, SUPABASE_AUTH_OPTIONS } from './supabaseConfig.js';

const { url, publishableKey } = getSupabaseConfig(import.meta.env ?? {});

export const supabase = createClient(url, publishableKey, {
  auth: SUPABASE_AUTH_OPTIONS,
});
