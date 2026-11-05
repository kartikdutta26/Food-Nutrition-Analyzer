import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const EMPTY_PROFILE = {
  name: '',
  age: '',
  height: '',
  weight: '',
  activityLevel: '',
  goal: '',
  waterTarget: '',
  dietary_preferences: [],
  targets: null,
};

test('profile page withholds personal fields while the authenticated profile is loading', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: ProfileSettings } = await vite.ssrLoadModule('/src/components/ProfileSettings.jsx');
    const markup = renderToStaticMarkup(createElement(ProfileSettings, {
      userProfile: { ...EMPTY_PROFILE, name: 'Account A private name' },
      onUpdateProfile: async () => true,
      isLoading: true,
    }));
    assert.match(markup, /Loading your saved profile/);
    assert.doesNotMatch(markup, /Account A private name/);
    assert.doesNotMatch(markup, /profile-name/);
  } finally {
    await vite.close();
  }
});

test('loaded empty profile is editable without requiring macro targets', async () => {
  const vite = await createServer({
    configFile: false,
    root: process.cwd(),
    server: { middlewareMode: true },
    appType: 'custom',
    logLevel: 'silent',
  });

  try {
    const { default: ProfileSettings } = await vite.ssrLoadModule('/src/components/ProfileSettings.jsx');
    const markup = renderToStaticMarkup(createElement(ProfileSettings, {
      userProfile: EMPTY_PROFILE,
      onUpdateProfile: async () => true,
      isLoaded: true,
    }));
    assert.match(markup, /id="profile-name"/);
    assert.match(markup, /id="profile-age"/);
    assert.match(markup, /id="profile-height"/);
    assert.match(markup, /id="profile-weight"/);
    assert.match(markup, /id="profile-activity"/);
    assert.match(markup, /Goal preference/);
    assert.doesNotMatch(markup, /required=""/);
    assert.doesNotMatch(markup, /session only|local only|local profile details/i);
    assert.match(markup, /Save Profile &amp; Targets/);
  } finally {
    await vite.close();
  }
});
