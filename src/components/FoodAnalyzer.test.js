import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('Food Analyzer renders a Search submit button beside the food input', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: FoodAnalyzer } = await vite.ssrLoadModule(
      '/src/components/FoodAnalyzer.jsx',
    );
    const markup = renderToStaticMarkup(createElement(FoodAnalyzer, {
      onAnalysisComplete: () => {},
      onAnalyzeFood: async () => ({}),
    }));
    const formStart = markup.indexOf('<form id="food-name-lookup-form"');
    const formEnd = markup.indexOf('</form>', formStart);
    const inputPosition = markup.indexOf('aria-label="Food name"', formStart);
    const buttonPosition = markup.indexOf('type="submit"', inputPosition);

    assert.notEqual(formStart, -1);
    assert.ok(inputPosition > formStart && inputPosition < formEnd);
    assert.ok(buttonPosition > inputPosition && buttonPosition < formEnd);
    assert.match(markup.slice(buttonPosition, formEnd), />Search<\/span>/);

    const componentSource = await readFile(new URL('./FoodAnalyzer.jsx', import.meta.url), 'utf8');
    assert.match(componentSource, /<form[^>]*onSubmit=\{handleAnalyze\}/s);
    assert.match(componentSource, /await runLookup\(lookup, normalizedName, \{ showMatches: true \}\)/);
  } finally {
    await vite.close();
  }
});
