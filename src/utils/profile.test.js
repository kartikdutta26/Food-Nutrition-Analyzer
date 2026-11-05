import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EMPTY_USER_PROFILE,
  getProfileInitial,
  profileFromApi,
  profileUpdateToApi,
} from './profile.js';

test('new profiles start empty rather than displaying shared sample details', () => {
  assert.deepEqual(EMPTY_USER_PROFILE, {
    name: '',
    age: '',
    height: '',
    weight: '',
    activityLevel: '',
    goal: '',
    waterTarget: '',
    dietary_preferences: [],
    targets: null,
  });
});

test('profile avatar initials use the saved name and fall back to the account email', () => {
  assert.equal(getProfileInitial('Kartik Dutta', 'kartik@example.com'), 'K');
  assert.equal(getProfileInitial('Maya Rao', 'kartik@example.com'), 'M');
  assert.equal(getProfileInitial('  ', 'kartik@example.com'), 'K');
  assert.equal(getProfileInitial('', ''), '?');
});

test('profile API response hydrates all persisted personal fields and nutrition targets', () => {
  assert.deepEqual(profileFromApi({
    name: 'Kartik Dutta',
    age: 29,
    height_cm: 181,
    weight_kg: 78,
    activity_level: 'Active',
    goal: 'Gain Muscle',
    water_liters: 3,
    dietary_preferences: ['Vegetarian'],
    targets: { calories: 2500, protein: 150, carbs: 280, fats: 75 },
  }), {
    name: 'Kartik Dutta',
    age: 29,
    height: 181,
    weight: 78,
    activityLevel: 'Active',
    goal: 'Gain Muscle',
    waterTarget: 3,
    dietary_preferences: ['Vegetarian'],
    targets: { calories: 2500, protein: 150, carbs: 280, fats: 75 },
  });
});

test('profile update sends personal details and keeps macro targets optional', () => {
  assert.deepEqual(profileUpdateToApi({
    name: ' Kartik Dutta ',
    age: '29',
    height: '181',
    weight: '78',
    activityLevel: 'Active',
    goal: 'Gain Muscle',
    waterTarget: '3',
    dietary_preferences: ['Vegetarian'],
    targets: { calories: '', protein: '', carbs: '', fats: '' },
  }), {
    name: 'Kartik Dutta',
    age: 29,
    height_cm: 181,
    weight_kg: 78,
    activity_level: 'Active',
    goal: 'Gain Muscle',
    water_liters: 3,
    dietary_preferences: ['Vegetarian'],
  });
});
