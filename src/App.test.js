import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('App renders its initial authentication state without a runtime exception', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: App } = await vite.ssrLoadModule('/src/App.jsx');
    const markup = renderToStaticMarkup(createElement(App));

    assert.match(markup, /class="auth-loading"/);
    assert.match(markup, /Restoring your secure session/);
  } finally {
    await vite.close();
  }
});
