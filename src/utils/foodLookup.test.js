import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildFoodLookupRequest,
  buildFoodMealRequest,
  formatFoodLookupError,
  getFoodMatchChoices,
  submitFoodNameLookup,
} from './foodLookup.js';

test('food lookup errors distinguish no match from service failures', () => {
  assert.match(
    formatFoodLookupError({ status: 404 }, 'dragonfruit smoothie'),
    /No USDA FoodData Central match.*dragonfruit smoothie/,
  );
  assert.equal(
    formatFoodLookupError({ status: 404, message: 'USDA FoodData Central found this food but does not report complete macros.' }, 'apple'),
    'USDA FoodData Central found this food but does not report complete macros.',
  );
  assert.equal(
    formatFoodLookupError({ status: 503, message: 'Add USDA_API_KEY to backend/.env.' }, 'apple'),
    'Add USDA_API_KEY to backend/.env.',
  );
});

test('food search submission trims the name and rejects an empty query', () => {
  assert.deepEqual(buildFoodLookupRequest('  banana  '), { food_name: 'banana' });
  assert.equal(buildFoodLookupRequest('   '), null);
});

test('food search submission invokes the backend lookup with the entered name', async () => {
  const expectedResponse = { name: 'Bananas, raw' };
  let submitted;
  const signal = new AbortController().signal;
  const response = await submitFoodNameLookup(
    ' Banana ',
    async (request, options) => {
      submitted = { request, signal: options.signal };
      return expectedResponse;
    },
    { signal },
  );

  assert.deepEqual(submitted, { request: { food_name: 'Banana' }, signal });
  assert.equal(response, expectedResponse);
  assert.equal(await submitFoodNameLookup(' ', () => assert.fail('empty lookup ran')), null);
});

test('food match selection only offers multiple valid backend matches', () => {
  const onlyMatch = { matches: [{ fdc_id: 1, name: 'Bananas, raw' }] };
  assert.deepEqual(getFoodMatchChoices(onlyMatch), []);

  const multipleMatches = {
    matches: [
      { fdc_id: 1, name: 'Bananas, raw' },
      { fdc_id: 2, name: 'Banana, frozen' },
      { fdc_id: 3, name: '' },
    ],
  };
  assert.deepEqual(getFoodMatchChoices(multipleMatches), multipleMatches.matches.slice(0, 2));
  assert.deepEqual(getFoodMatchChoices({}), []);
});

test('sample preset food keeps using the preset meal endpoint shape', () => {
  assert.deepEqual(
    buildFoodMealRequest(
      { data_source: 'sample_preset', preset_id: 'paneer-rice' },
      'Lunch',
      {},
      1,
    ),
    { preset_id: 'paneer-rice', meal_slot: 'Lunch' },
  );
});

test('USDA food log payload preserves its source and scales the selected serving', () => {
  const nutrition = { calories: 90, protein: 1.2, carbs: 24, fats: 0.3, fiber: null };
  const payload = buildFoodMealRequest({
    name: 'Apples, raw, with skin',
    data_source: 'usda_food_data_central',
    fdc_id: 12345,
    serving: { description: '1 cup, sliced (109 g)', gram_weight: 109 },
  }, 'Snack', nutrition, 1.5);

  assert.deepEqual(payload, {
    name: 'Apples, raw, with skin',
    meal_slot: 'Snack',
    nutrition,
    data_source: 'usda_food_data_central',
    fdc_id: 12345,
    serving: { description: '1.5× 1 cup, sliced (109 g)', gram_weight: 163.5 },
  });
});
