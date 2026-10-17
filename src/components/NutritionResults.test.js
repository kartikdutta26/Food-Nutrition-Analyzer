import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('Nutrition Results renders the selected USDA serving, values, and photo fallback', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: NutritionResults } = await vite.ssrLoadModule(
      '/src/components/NutritionResults.jsx',
    );
    const markup = renderToStaticMarkup(createElement(NutritionResults, {
      meal: {
        name: 'Apples, raw, with skin',
        fdc_id: 12345,
        serving: { description: '1 medium (182 g)', gram_weight: 182 },
        nutrition: { calories: 95, protein: 0.5, carbs: 25, fats: 0.3, fiber: 4.4 },
        data_source: 'usda_food_data_central',
        notice: 'Values from USDA FoodData Central.',
      },
      userTargets: null,
      onLogMeal: async () => true,
      onScanAnother: () => {},
      onNavigateToDashboard: () => {},
    }));

    assert.match(markup, /Apples, raw, with skin/);
    assert.match(markup, /1 medium \(182 g\)/);
    assert.match(markup, /FoodData Central/);
    assert.match(markup, /95 kcal/);
    assert.match(markup, /25 g/);
    assert.match(markup, /Food photo unavailable/);
    assert.doesNotMatch(markup, /Photograph related to Apples/);
  } finally {
    await vite.close();
  }
});
