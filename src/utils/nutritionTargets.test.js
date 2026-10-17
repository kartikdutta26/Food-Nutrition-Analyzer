import assert from 'node:assert/strict';
import test from 'node:test';
import { getTargetProgress, hasNutritionTargets, validateNutritionTargets } from './nutritionTargets.js';

test('unset dashboard targets prompt configuration after profile loads', () => {
  const progress = getTargetProgress(null, 425, true);

  assert.deepEqual(progress, {
    configured: false,
    target: null,
    percent: null,
    label: 'Configure target in Profile',
  });
  assert.equal(hasNutritionTargets(null), false);
});

test('dashboard progress uses the saved target returned by the profile', () => {
  const targets = { calories: 2000, protein: 100, carbs: 200, fats: 60 };

  assert.deepEqual(getTargetProgress(targets.calories, 500, true), {
    configured: true,
    target: 2000,
    percent: 25,
    label: '25%',
  });
  assert.equal(hasNutritionTargets(targets), true);
});

test('dashboard distinguishes targets that have not loaded yet', () => {
  assert.equal(getTargetProgress(undefined, 0, false).label, 'Target not loaded');
});

test('missing individual saved targets remain unconfigured', () => {
  const partialTargets = { calories: 2000, protein: null, carbs: 200, fats: 60 };

  assert.equal(getTargetProgress(partialTargets.protein, 500, true).configured, false);
  assert.equal(getTargetProgress(partialTargets.protein, 500, true).target, null);
  assert.equal(hasNutritionTargets(partialTargets), false);
});

test('dashboard never calculates progress from a non-positive target', () => {
  assert.equal(getTargetProgress(0, 100, true).configured, false);
});

test('profile target validation accepts a complete positive target set', () => {
  assert.equal(validateNutritionTargets({ calories: '1900', protein: '95', carbs: '210', fats: '65' }), '');
});

test('profile target validation explains missing, non-positive, and out-of-range values', () => {
  const completeTargets = { calories: '1900', protein: '95', carbs: '210', fats: '65' };

  assert.equal(validateNutritionTargets({ ...completeTargets, protein: '' }), 'protein must be a number greater than 0.');
  assert.equal(validateNutritionTargets({ ...completeTargets, carbs: '0' }), 'carbs must be a number greater than 0.');
  assert.equal(validateNutritionTargets({ ...completeTargets, fats: '10001' }), 'fats must not exceed 10000.');
});
