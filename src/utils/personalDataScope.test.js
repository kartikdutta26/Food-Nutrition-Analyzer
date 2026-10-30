import test from 'node:test';
import assert from 'node:assert/strict';
import { createPersonalDataScope, resetPersonalDataState } from './personalDataScope.js';

test('account switching makes a previous user request stale before it can publish results', async () => {
  const scope = createPersonalDataScope();
  scope.setUserId('user-a');
  const previousUserRequest = scope.capture();
  let resolveRequest;
  const request = new Promise((resolve) => { resolveRequest = resolve; });
  const visibleMeals = [];
  const completion = request.then((meal) => {
    if (scope.isCurrent(previousUserRequest)) visibleMeals.push(meal);
  });

  scope.setUserId('user-b');
  resolveRequest({ id: 'meal-a', name: 'Previous account meal' });
  await completion;

  assert.equal(scope.isCurrent(previousUserRequest), false);
  assert.deepEqual(visibleMeals, []);
  assert.equal(scope.isCurrent(scope.capture()), true);
});

test('logout invalidates in-flight reads and clears all user-specific values and loading flags', () => {
  const scope = createPersonalDataScope('user-a');
  const inFlight = scope.capture();
  const state = {
    todayLog: { meals: [{ id: 'private-meal' }] },
    dailyTotals: { calories: 900 },
    dailyLoading: true,
    dailyError: 'old error',
    mealActionError: 'old meal error',
    isSavingMeal: true,
    pendingMealId: 'private-meal',
    isLoggingAnalysisMeal: true,
    userProfile: { dietary_preferences: ['private preference'], targets: { calories: 1 } },
    profileLoading: true,
    profileLoaded: true,
    profileError: 'old profile error',
    profileActionError: 'old profile action error',
    isSavingProfile: true,
  };
  const setters = Object.fromEntries(Object.keys(state).map((key) => [
    `set${key[0].toUpperCase()}${key.slice(1)}`,
    (value) => { state[key] = value; },
  ]));

  scope.invalidate();
  resetPersonalDataState(setters, {
    initialProfile: { name: 'Guest', age: 0 },
    emptyTotals: { calories: 0, protein: 0, carbs: 0, fats: 0, fiber: 0 },
  });

  assert.equal(scope.isCurrent(inFlight), false);
  assert.deepEqual(state, {
    todayLog: { meals: [] },
    dailyTotals: { calories: 0, protein: 0, carbs: 0, fats: 0, fiber: 0 },
    dailyLoading: false,
    dailyError: '',
    mealActionError: '',
    isSavingMeal: false,
    pendingMealId: null,
    isLoggingAnalysisMeal: false,
    userProfile: { name: 'Guest', age: 0, dietary_preferences: [], targets: null },
    profileLoading: false,
    profileLoaded: false,
    profileError: '',
    profileActionError: '',
    isSavingProfile: false,
  });
});
