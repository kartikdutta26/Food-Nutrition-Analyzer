import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('daily dashboard still renders saved meal rows and nutrition totals', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: DailyDashboard } = await vite.ssrLoadModule('/src/components/DailyDashboard.jsx');
    const markup = renderToStaticMarkup(createElement(DailyDashboard, {
      todayLog: {
        meals: [{
          id: 'meal-1',
          name: 'Paneer Rice Bowl',
          slot: 'Lunch',
          time: '12:30',
          calories: 620,
          protein: 28,
          carbs: 72,
          fats: 22,
          fiber: 6,
          dataSource: 'sample_preset',
        }],
      },
      dailyTotals: { calories: 620, protein: 28, carbs: 72, fats: 22, fiber: 6 },
      dailyDate: '2026-10-26',
      isLoading: false,
      profileLoaded: true,
      userProfile: { targets: { calories: 2000, protein: 100, carbs: 200, fats: 60 } },
      onRetry: () => {},
      onRetryProfile: () => {},
      onNavigateToProfile: () => {},
      onAddMealFromDaily: async () => true,
      onNavigateToAnalyzer: () => {},
      onRemoveMeal: () => {},
    }));

    assert.match(markup, /Today&#x27;s Meals/);
    assert.match(markup, /Paneer Rice Bowl/);
    assert.match(markup, /Sample preset nutrition/);
    assert.match(markup, /Log Meal Manually/);
  } finally {
    await vite.close();
  }
});
