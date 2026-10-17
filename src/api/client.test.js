import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeFood, fetchFoodPhoto } from './client.js';

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
