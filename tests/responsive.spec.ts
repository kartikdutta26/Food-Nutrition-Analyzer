import { expect, test, type Page, type TestInfo } from '@playwright/test';

const viewports = [320, 375, 768];

async function expectNoHorizontalOverflow(page: Page) {
  const hasNoHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(hasNoHorizontalOverflow, 'page should fit the viewport horizontally').toBe(true);
}

async function captureNarrowScreenshot(
  page: Page,
  testInfo: TestInfo,
  name: string,
  width: number,
) {
  if (width === 320) {
    await testInfo.attach(`${name}-${width}px.png`, {
      body: await page.screenshot({ fullPage: true }),
      contentType: 'image/png',
    });
  }
}

async function openMobileSection(page: Page, name: string) {
  await page.getByRole('button', { name: 'Open navigation menu' }).click();
  await page.locator('#mobile-navigation').getByRole('button', { name }).click();
}

test('login and signup fit narrow viewports', async ({ page }, testInfo) => {
  await page.goto('/login');

  for (const width of viewports) {
    await page.setViewportSize({ width, height: 812 });
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'login', width);

    await page.getByRole('tab', { name: 'Sign Up' }).click();
    await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'signup', width);
    await page.getByRole('tab', { name: 'Login' }).click();
  }
});

test('main app screens and meal logging fit responsive viewports', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 320, height: 812 });
  await page.goto('/login');
  await page.getByRole('button', { name: 'Explore in demo mode' }).click();

  for (const width of viewports) {
    await page.setViewportSize({ width, height: 812 });
    await openMobileSection(page, 'Home');
    await expect(page.getByRole('heading', { name: 'Know what’s on your plate.' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'home', width);

    await openMobileSection(page, 'Analyze food');
    await expect(page.getByRole('heading', { name: 'Analyze Your Meal' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'analyzer', width);

    await page.getByRole('button', { name: /Take a Photo/ }).click();
    await expect(page.getByRole('heading', { name: 'Smart Camera Viewfinder' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.getByRole('button', { name: /Enter Food Manually/ }).click();
    await expect(page.getByRole('textbox', { name: /Search Indian or global dish/ })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.getByRole('button', { name: /Analyze Nutritional Value/ }).click();
    await expect(page.getByRole('button', { name: 'Analyze Another Meal' })).toBeVisible({
      timeout: 10_000,
    });
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'results', width);

    await openMobileSection(page, 'Nutrition journey');
    await expect(page.getByRole('heading', { name: "Today's Nutrition" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'daily-dashboard', width);

    if (width === 320) {
      await page.getByRole('button', { name: 'Log Meal Manually' }).click();
      await page.getByRole('textbox', { name: 'e.g. Mixed Dal with 2 Rotis' }).fill('Mobile test meal');
      await page.getByRole('button', { name: 'Save Entry' }).click();
      await expect(page.getByRole('heading', { name: 'Mobile test meal' })).toBeVisible();
      await expectNoHorizontalOverflow(page);
    }

    await openMobileSection(page, 'Profile & goals');
    await expect(page.getByRole('heading', { name: 'Personal Nutrition Profile' })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await captureNarrowScreenshot(page, testInfo, 'profile', width);
  }
});
