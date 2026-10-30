const configuredBaseUrl = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
const API_BASE_URL = configuredBaseUrl.replace(/\/+$/, '');
const FOOD_PHOTO_CACHE_TTL_MS = 15 * 60 * 1000;

export class ApiError extends Error {
  constructor(message, status = 0, code = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
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

async function getCurrentSession() {
  const { supabase } = await import('../lib/supabase.js');
  const { data, error } = await supabase.auth.getSession();
  if (error) throw new ApiError('Your session could not be checked. Please sign in again.', 401);
  return data?.session ?? null;
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

/**
 * Build an API client with injectable fetch/session providers for isolated tests.
 * Personal-data methods require a current Supabase session and never send an
 * owner identifier to FastAPI; the backend derives ownership from the token.
 */
export function createApiClient({
  baseUrl = API_BASE_URL,
  fetchImpl = (...args) => fetch(...args),
  sessionProvider = getCurrentSession,
} = {}) {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, '');
  const foodPhotoCache = new Map();

  async function request(path, {
    method = 'GET',
    body,
    signal,
    authenticated = false,
    expectedUserId,
  } = {}) {
    const headers = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    if (authenticated) {
      let session;
      try {
        session = await sessionProvider();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) throw error;
        throw new ApiError('Your session could not be checked. Please sign in again.', 401);
      }

      const accessToken = session?.access_token;
      if (!accessToken) {
        throw new ApiError('Your session has expired. Please sign in again.', 401);
      }
      if (expectedUserId && session?.user?.id !== expectedUserId) {
        throw new ApiError('The signed-in account changed. Refreshing personal data for the current account.', 401, 'SESSION_USER_CHANGED');
      }
      headers.Authorization = `Bearer ${accessToken}`;
    }

    let response;
    try {
      response = await fetchImpl(`${normalizedBaseUrl}${path}`, {
        method,
        headers: Object.keys(headers).length ? headers : undefined,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (error) {
      if (error?.name === 'AbortError') throw error;
      throw new ApiError(
        `Cannot reach the NutriAI API at ${normalizedBaseUrl}. Check that the backend is running and CORS allows this frontend origin.`,
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
      if (authenticated && response.status === 401) {
        throw new ApiError('Your session is invalid or expired. Sign in again to access personal data.', 401);
      }
      if (authenticated && response.status === 403) {
        throw new ApiError('Verify your email address before accessing personal data.', 403);
      }
      if (response.status === 503 || response.status === 502) {
        const message = authenticated
          ? 'NutriAI personal-data services are temporarily unavailable. Try again shortly.'
          : 'NutriAI is temporarily unavailable. Try again shortly.';
        throw new ApiError(message, response.status);
      }
      if (response.status >= 500) {
        throw new ApiError('NutriAI could not complete this request because of a server configuration or internal error.', response.status);
      }
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

  function fetchMealsForDate(date, { expectedUserId, signal } = {}) {
    const query = new URLSearchParams({ date, limit: '500' });
    return request(`/api/meals?${query.toString()}`, {
      authenticated: true, expectedUserId, signal,
    });
  }

  function fetchDailyNutrition(date, { expectedUserId, signal } = {}) {
    const query = new URLSearchParams({ date });
    return request(`/api/nutrition/daily?${query.toString()}`, {
      authenticated: true, expectedUserId, signal,
    });
  }

  function createMeal(meal, { expectedUserId, signal } = {}) {
    return request('/api/meals', {
      method: 'POST', body: meal, authenticated: true, expectedUserId, signal,
    });
  }

  function deleteMeal(mealId, { expectedUserId, signal } = {}) {
    return request(`/api/meals/${encodeURIComponent(mealId)}`, {
      method: 'DELETE', authenticated: true, expectedUserId, signal,
    });
  }

  function analyzeFood(foodInput, { signal } = {}) {
    return request('/api/food/analyze', { method: 'POST', body: foodInput, signal });
  }

  function fetchFoodPhoto(foodName, { signal } = {}) {
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

  function fetchProfile({ expectedUserId, signal } = {}) {
    return request('/api/profile', { authenticated: true, expectedUserId, signal });
  }

  function updateProfile(profileUpdate, { expectedUserId, signal } = {}) {
    return request('/api/profile', {
      method: 'PATCH', body: profileUpdate, authenticated: true, expectedUserId, signal,
    });
  }

  return {
    fetchMealsForDate,
    fetchDailyNutrition,
    createMeal,
    deleteMeal,
    analyzeFood,
    fetchFoodPhoto,
    fetchProfile,
    updateProfile,
  };
}

const apiClient = createApiClient();

export const fetchMealsForDate = (...args) => apiClient.fetchMealsForDate(...args);
export const fetchDailyNutrition = (...args) => apiClient.fetchDailyNutrition(...args);
export const createMeal = (...args) => apiClient.createMeal(...args);
export const deleteMeal = (...args) => apiClient.deleteMeal(...args);
export const analyzeFood = (...args) => apiClient.analyzeFood(...args);
export const fetchFoodPhoto = (...args) => apiClient.fetchFoodPhoto(...args);
export const fetchProfile = (...args) => apiClient.fetchProfile(...args);
export const updateProfile = (...args) => apiClient.updateProfile(...args);
