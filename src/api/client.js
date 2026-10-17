const configuredBaseUrl = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_BASE_URL = configuredBaseUrl.replace(/\/+$/, '');
const FOOD_PHOTO_CACHE_TTL_MS = 15 * 60 * 1000;
const foodPhotoCache = new Map();

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function formatDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((issue) => {
      const field = (issue.loc || [])
        .filter((part) => !['body', 'query', 'path'].includes(part))
        .join('.');
      return field ? `${field}: ${issue.msg || 'Invalid value'}` : issue.msg || 'Invalid value';
    }).join('; ');
  }

  return typeof detail === 'string' ? detail : '';
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    throw new ApiError(
      `Cannot reach the NutriAI API at ${API_BASE_URL}. Check that the backend is running and CORS allows this frontend origin.`,
    );
  }

  if (response.status === 204) return null;

  let payload;
  try {
    payload = await response.json();
  } catch {
    if (response.ok) {
      throw new ApiError('The backend returned an unreadable response.', response.status);
    }
  }

  if (!response.ok) {
    const detail = formatDetail(payload?.detail);
    const message = detail && response.status === 422
      ? `Validation error: ${detail}`
      : detail;
    throw new ApiError(
      message || `The backend request failed with status ${response.status}.`,
      response.status,
    );
  }

  return payload;
}

export function fetchMealsForDate(date) {
  const query = new URLSearchParams({ date, limit: '500' });
  return request(`/api/meals?${query.toString()}`);
}

export function fetchDailyNutrition(date) {
  const query = new URLSearchParams({ date });
  return request(`/api/nutrition/daily?${query.toString()}`);
}

export function createMeal(meal) {
  return request('/api/meals', { method: 'POST', body: meal });
}

export function deleteMeal(mealId) {
  return request(`/api/meals/${encodeURIComponent(mealId)}`, { method: 'DELETE' });
}

export function analyzeFood(foodInput, { signal } = {}) {
  return request('/api/food/analyze', { method: 'POST', body: foodInput, signal });
}

function observeWithAbort(promise, signal) {
  if (!signal) return promise;
  if (signal.aborted) {
    const error = new Error('The photo request was aborted.');
    error.name = 'AbortError';
    return Promise.reject(error);
  }

  return new Promise((resolve, reject) => {
    const onAbort = () => {
      const error = new Error('The photo request was aborted.');
      error.name = 'AbortError';
      reject(error);
    };
    signal.addEventListener('abort', onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener('abort', onAbort);
        resolve(value);
      },
      (error) => {
        signal.removeEventListener('abort', onAbort);
        reject(error);
      },
    );
  });
}

export function fetchFoodPhoto(foodName, { signal } = {}) {
  const normalizedName = typeof foodName === 'string' ? foodName.trim() : '';
  if (!normalizedName) return Promise.resolve(null);

  const cacheKey = normalizedName.toLowerCase();
  const cached = foodPhotoCache.get(cacheKey);
  if (cached?.promise) return observeWithAbort(cached.promise, signal);
  if (cached && cached.expiresAt > Date.now()) {
    return observeWithAbort(Promise.resolve(cached.photo), signal);
  }

  const query = new URLSearchParams({ food_name: normalizedName });
  const pending = request(`/api/food/photo?${query.toString()}`)
    .catch((error) => {
      if (error?.status === 404) return null;
      throw error;
    })
    .then((photo) => {
      foodPhotoCache.set(cacheKey, { photo, expiresAt: Date.now() + FOOD_PHOTO_CACHE_TTL_MS });
      return photo;
    })
    .catch((error) => {
      foodPhotoCache.delete(cacheKey);
      throw error;
    });
  foodPhotoCache.set(cacheKey, { promise: pending, expiresAt: Number.POSITIVE_INFINITY });
  return observeWithAbort(pending, signal);
}

export function fetchProfile() {
  return request('/api/profile');
}

export function updateProfile(profileUpdate) {
  return request('/api/profile', { method: 'PATCH', body: profileUpdate });
}
