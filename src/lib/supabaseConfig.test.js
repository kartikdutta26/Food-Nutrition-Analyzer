import assert from 'node:assert/strict';
import test from 'node:test';
import { getSupabaseConfig, SUPABASE_AUTH_OPTIONS } from './supabaseConfig.js';

test('browser auth explicitly uses the SDK-managed implicit callback and session restoration flow', () => {
  assert.deepEqual(SUPABASE_AUTH_OPTIONS, {
    flowType: 'implicit',
    detectSessionInUrl: true,
    persistSession: true,
    autoRefreshToken: true,
  });
});

test('reads and trims the Supabase URL and publishable key', () => {
  const config = getSupabaseConfig({
    VITE_SUPABASE_URL: ' https://project.supabase.co ',
    VITE_SUPABASE_PUBLISHABLE_KEY: ' sb_publishable_test-value ',
  });

  assert.deepEqual(config, {
    url: 'https://project.supabase.co',
    publishableKey: 'sb_publishable_test-value',
  });
});

test('reports missing Supabase variable names without echoing other configured values', () => {
  assert.throws(
    () => getSupabaseConfig({
      VITE_SUPABASE_URL: 'https://private-project-ref.supabase.co',
      VITE_SUPABASE_PUBLISHABLE_KEY: ' ',
    }),
    (error) => {
      assert.match(error.message, /VITE_SUPABASE_PUBLISHABLE_KEY/);
      assert.doesNotMatch(error.message, /private-project-ref/);
      return true;
    },
  );
});

test('reports both required variables when neither is configured', () => {
  assert.throws(
    () => getSupabaseConfig({}),
    (error) => {
      assert.match(error.message, /VITE_SUPABASE_URL/);
      assert.match(error.message, /VITE_SUPABASE_PUBLISHABLE_KEY/);
      return true;
    },
  );
});

test('rejects a malformed URL without echoing it', () => {
  assert.throws(
    () => getSupabaseConfig({
      VITE_SUPABASE_URL: 'not-a-url-sensitive-value',
      VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_test-value',
    }),
    (error) => {
      assert.match(error.message, /VITE_SUPABASE_URL/);
      assert.doesNotMatch(error.message, /not-a-url-sensitive-value/);
      return true;
    },
  );
});
