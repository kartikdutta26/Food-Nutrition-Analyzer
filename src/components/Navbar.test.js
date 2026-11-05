import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

test('desktop and mobile authenticated navigation render an account avatar and account menu trigger', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: Navbar } = await vite.ssrLoadModule('/src/components/Navbar.jsx');
    const markup = renderToStaticMarkup(createElement(Navbar, {
      activeTab: 'home',
      setActiveTab: () => {},
      onSignOut: () => {},
      authUser: { id: 'user-a', email: 'kartik@example.com' },
      profileName: 'Kartik Dutta',
    }));

    assert.match(markup, /class="account-avatar"[^>]*>K<\/span>/);
    assert.match(markup, /class="account-display-name">Kartik Dutta<\/span>/);
    assert.match(markup, /aria-label="Account menu for Kartik Dutta"/);
    assert.match(markup, /class="mobile-account"/);
    assert.match(markup, /account-menu--compact/);
    assert.match(markup, /aria-label="Main navigation"/);
    assert.match(markup, /aria-label="Open navigation menu"/);
  } finally {
    await vite.close();
  }
});

test('account dropdown exposes profile and sign out actions without unsupported settings links', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { AccountMenuPopover } = await vite.ssrLoadModule('/src/components/Navbar.jsx');
    const markup = renderToStaticMarkup(createElement(AccountMenuPopover, {
      id: 'account-menu-test',
      name: 'Kartik Dutta',
      email: 'kartik@example.com',
      initial: 'K',
      onProfile: () => {},
      onSignOut: () => {},
    }));
    assert.match(markup, /role="menu" aria-label="Account"/);
    assert.match(markup, /role="menuitem"[^>]*>.*My Profile/);
    assert.match(markup, /role="menuitem"[^>]*>.*Sign Out/);
    assert.doesNotMatch(markup, /Account Settings/);
  } finally {
    await vite.close();
  }
});

test('responsive account styles expose the compact avatar and mobile dropdown placement', async () => {
  const css = await readFile(new URL('../index.css', import.meta.url), 'utf8');
  assert.match(css, /\.account-menu-trigger/);
  assert.match(css, /\.account-display-name/);
  assert.match(css, /@media \(max-width: 1180px\)[\s\S]*?\.mobile-account \{ display: block; \}/);
  assert.match(css, /\.account-menu--compact \.account-menu-trigger/);
  assert.match(css, /@media \(max-width: 560px\)[\s\S]*?\.account-menu--compact \.account-menu-popover \{ position: fixed;/);
});

test('mobile and desktop account avatar falls back to the signed-in email before profile load', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: Navbar } = await vite.ssrLoadModule('/src/components/Navbar.jsx');
    const markup = renderToStaticMarkup(createElement(Navbar, {
      activeTab: 'home',
      setActiveTab: () => {},
      onSignOut: () => {},
      authUser: { id: 'user-a', email: 'alice@example.com' },
    }));
    assert.match(markup, /class="account-avatar"[^>]*>A<\/span>/);
    assert.match(markup, /class="account-display-name">alice@example\.com<\/span>/);
  } finally {
    await vite.close();
  }
});
