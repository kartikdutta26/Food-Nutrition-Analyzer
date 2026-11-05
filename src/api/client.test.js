import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeFood, ApiError, createApiClient, fetchFoodPhoto } from './client.js';

test('food-name lookup sends the name to the backend without a USDA key', async () => {
  const originalFetch = globalThis.fetch;
  let requestUrl;
  let requestOptions;
  globalThis.fetch = async (url, options) => {
    requestUrl = url;
    requestOptions = options;
    return new Response(JSON.stringify({ data_source: 'usda_food_data_central' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const result = await analyzeFood({ food_name: 'apple' });
    assert.match(requestUrl, /\/api\/food\/analyze$/);
    assert.deepEqual(JSON.parse(requestOptions.body), { food_name: 'apple' });
    assert.equal(JSON.stringify(requestOptions).includes('USDA_API_KEY'), false);
    assert.equal(result.data_source, 'usda_food_data_central');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('food-name lookup forwards AbortSignal and preserves cancellation', async () => {
  const originalFetch = globalThis.fetch;
  const controller = new AbortController();
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.signal, controller.signal);
    throw new DOMException('Request aborted', 'AbortError');
  };

  try {
    await assert.rejects(
      analyzeFood({ food_name: 'apple' }, { signal: controller.signal }),
      { name: 'AbortError' },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('selected USDA match is resolved through the same backend endpoint', async () => {
  const originalFetch = globalThis.fetch;
  let requestUrl;
  let requestOptions;
  globalThis.fetch = async (url, options) => {
    requestUrl = url;
    requestOptions = options;
    return new Response(JSON.stringify({
      fdc_id: 202,
      name: 'Bananas, frozen',
      data_source: 'usda_food_data_central',
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const result = await analyzeFood({ food_name: 'banana', fdc_id: 202 });
    assert.match(requestUrl, /\/api\/food\/analyze$/);
    assert.deepEqual(JSON.parse(requestOptions.body), { food_name: 'banana', fdc_id: 202 });
    assert.equal(result.fdc_id, 202);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('food photo lookup uses the backend and reuses its cached result', async () => {
  const originalFetch = globalThis.fetch;
  const photo = {
    image_url: 'https://images.unsplash.com/photo-test',
    photographer_name: 'Test Photographer',
    photographer_profile_url: 'https://unsplash.com/@test',
    attribution_url: 'https://unsplash.com/photos/test',
  };
  let requestUrl;
  let requestCount = 0;
  globalThis.fetch = async (url, options) => {
    requestUrl = url;
    requestCount += 1;
    assert.equal(options.method, 'GET');
    assert.equal(options.body, undefined);
    return new Response(JSON.stringify(photo), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  try {
    const first = await fetchFoodPhoto('  test food photo cache  ');
    const second = await fetchFoodPhoto('TEST FOOD PHOTO CACHE');
    const parsedUrl = new URL(requestUrl);
    assert.match(parsedUrl.pathname, /\/api\/food\/photo$/);
    assert.equal(parsedUrl.searchParams.get('food_name'), 'test food photo cache');
    assert.deepEqual(first, photo);
    assert.deepEqual(second, photo);
    assert.equal(requestCount, 1);
    assert.equal(await fetchFoodPhoto('  '), null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('aborting a stale food-photo consumer leaves the shared lookup available', async () => {
  const originalFetch = globalThis.fetch;
  const controller = new AbortController();
  const photo = {
    image_url: 'https://images.unsplash.com/photo-stale-check',
    photographer_name: 'Test Photographer',
    photographer_profile_url: 'https://unsplash.com/@test',
    attribution_url: 'https://unsplash.com/photos/stale-check',
  };
  let resolveFetch;
  let requestCount = 0;
  globalThis.fetch = async () => {
    requestCount += 1;
    return new Promise((resolve) => { resolveFetch = resolve; });
  };

  try {
    const staleRequest = fetchFoodPhoto('stale photo selection', { signal: controller.signal });
    controller.abort();
    await assert.rejects(staleRequest, { name: 'AbortError' });

    const currentRequest = fetchFoodPhoto('stale photo selection');
    resolveFetch(new Response(JSON.stringify(photo), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }));
    assert.deepEqual(await currentRequest, photo);
    assert.equal(requestCount, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('personal-data methods attach the current Supabase bearer token and use backend contracts', async () => {
  const requests = [];
  const client = createApiClient({
    baseUrl: 'http://api.test/',
    sessionProvider: async () => ({
      access_token: 'test-access-token',
      user: { id: 'user-1' },
    }),
    fetchImpl: async (url, options) => {
      requests.push({ url, options });
      return options.method === 'DELETE'
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
    },
  });

  await client.fetchProfile({ expectedUserId: 'user-1' });
  await client.updateProfile({
    name: 'Kartik Dutta',
    age: 29,
    height_cm: 181,
    weight_kg: 78,
    activity_level: 'Active',
    goal: 'Gain Muscle',
    water_liters: 3,
    dietary_preferences: ['vegetarian'],
  }, { expectedUserId: 'user-1' });
  await client.createMeal({ preset_id: 'oatmeal-bowl', meal_slot: 'Breakfast' }, { expectedUserId: 'user-1' });
  await client.fetchMealsForDate('2026-10-26', { expectedUserId: 'user-1' });
  await client.deleteMeal('abc123abc123abc123abc123', { expectedUserId: 'user-1' });
  await client.fetchDailyNutrition('2026-10-26', { expectedUserId: 'user-1' });

  assert.deepEqual(requests.map(({ url, options }) => [new URL(url).pathname, options.method]), [
    ['/api/profile', 'GET'],
    ['/api/profile', 'PATCH'],
    ['/api/meals', 'POST'],
    ['/api/meals', 'GET'],
    ['/api/meals/abc123abc123abc123abc123', 'DELETE'],
    ['/api/nutrition/daily', 'GET'],
  ]);
  for (const { options } of requests) {
    assert.equal(options.headers.Authorization, 'Bearer test-access-token');
  }
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    name: 'Kartik Dutta',
    age: 29,
    height_cm: 181,
    weight_kg: 78,
    activity_level: 'Active',
    goal: 'Gain Muscle',
    water_liters: 3,
    dietary_preferences: ['vegetarian'],
  });
  assert.deepEqual(JSON.parse(requests[2].options.body), {
    preset_id: 'oatmeal-bowl',
    meal_slot: 'Breakfast',
  });
  assert.equal(new URL(requests[3].url).searchParams.get('date'), '2026-10-26');
  assert.equal(new URL(requests[3].url).searchParams.get('limit'), '500');
  assert.equal(new URL(requests[5].url).searchParams.get('date'), '2026-10-26');
  assert.equal(requests.some(({ options }) => options.body?.includes('user_id')), false);
});

test('public food analysis and photo requests do not read or send a session token', async () => {
  let sessionReads = 0;
  const requests = [];
  const client = createApiClient({
    baseUrl: 'http://api.test',
    sessionProvider: async () => {
      sessionReads += 1;
      throw new Error('Public routes must not ask for a session');
    },
    fetchImpl: async (url, options) => {
      requests.push({ url, options });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    },
  });

  await client.analyzeFood({ food_name: 'apple' });
  await client.fetchFoodPhoto(`public-photo-${Date.now()}`);

  assert.equal(sessionReads, 0);
  assert.equal(requests.length, 2);
  assert.equal(requests[0].options.headers.Authorization, undefined);
  assert.equal(requests[1].options.headers, undefined);
});

test('personal-data requests fail safely before fetch when the session is absent or belongs to another user', async () => {
  let fetchCount = 0;
  const noSessionClient = createApiClient({
    sessionProvider: async () => null,
    fetchImpl: async () => { fetchCount += 1; },
  });
  await assert.rejects(noSessionClient.fetchProfile({ expectedUserId: 'user-1' }), {
    name: 'ApiError', status: 401,
  });
  assert.equal(fetchCount, 0);

  const switchedAccountClient = createApiClient({
    sessionProvider: async () => ({ access_token: 'other-token', user: { id: 'user-2' } }),
    fetchImpl: async () => { fetchCount += 1; },
  });
  await assert.rejects(
    switchedAccountClient.fetchProfile({ expectedUserId: 'user-1' }),
    (error) => error instanceof ApiError
      && error.status === 401
      && error.code === 'SESSION_USER_CHANGED',
  );
  assert.equal(fetchCount, 0);
});

test('backend 401 is surfaced without retrying the request', async () => {
  let fetchCount = 0;
  let sessionCount = 0;
  const client = createApiClient({
    sessionProvider: async () => {
      sessionCount += 1;
      return { access_token: 'test-access-token', user: { id: 'user-1' } };
    },
    fetchImpl: async () => {
      fetchCount += 1;
      return new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    },
  });

  await assert.rejects(client.fetchProfile({ expectedUserId: 'user-1' }), {
    name: 'ApiError', status: 401,
  });
  assert.equal(fetchCount, 1);
  assert.equal(sessionCount, 1);
});

test('protected API errors distinguish invalid sessions from temporary and configuration failures', async () => {
  const sessionProvider = async () => ({ access_token: 'test-access-token', user: { id: 'user-1' } });
  const responses = [
    [401, 'invalid or expired'],
    [403, 'Verify your email address'],
    [503, 'temporarily unavailable'],
    [500, 'server configuration or internal error'],
  ];

  for (const [status, expectedMessage] of responses) {
    const client = createApiClient({
      sessionProvider,
      fetchImpl: async () => new Response(JSON.stringify({ detail: 'sensitive internal detail' }), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
    });
    await assert.rejects(
      client.fetchProfile({ expectedUserId: 'user-1' }),
      (error) => error instanceof ApiError
        && error.status === status
        && error.message.includes(expectedMessage)
        && !error.message.includes('sensitive internal detail'),
    );
  }
});
