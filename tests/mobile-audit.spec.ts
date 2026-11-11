import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const viewports = [
  { width: 360, height: 800 },
  { width: 375, height: 812 },
  { width: 390, height: 844 },
  { width: 414, height: 896 },
  { width: 430, height: 932 },
];

type Finding = {
  level: 'FAIL' | 'WARN';
  category: string;
  detail: string;
};

type ScreenAudit = {
  screen: string;
  width: number;
  height: number;
  documentWidth: number;
  horizontalOverflow: number;
  outsideElements: Array<{
    tag: string;
    selector: string;
    text: string;
    left: number;
    right: number;
    interactive: boolean;
    expectedOverflow: boolean;
  }>;
  clippedText: Array<{ selector: string; text: string }>;
  cards: Array<{ selector: string; width: number; left: number; right: number }>;
  images: Array<{
    alt: string;
    loaded: boolean;
    settled: boolean;
    width: number;
    height: number;
    naturalWidth: number;
    naturalHeight: number;
    objectFit: string;
  }>;
  charts: Array<{ selector: string; width: number; left: number; right: number }>;
  buttons: {
    count: number;
    smallTargets: Array<{ selector: string; text: string; width: number; height: number }>;
    disabled: number;
  };
  forms: {
    count: number;
    controls: number;
    unusableControls: Array<{ selector: string; text: string; width: number; height: number }>;
  };
  findings: Finding[];
};

type ViewportAudit = {
  width: number;
  height: number;
  screens: ScreenAudit[];
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
};

async function auditScreen(page: Page, screen: string): Promise<ScreenAudit> {
  return page.evaluate(
    ({ screen, width, height }) => {
      const describe = (element: Element) => {
        const tag = element.tagName.toLowerCase();
        const id = element.id ? `#${element.id}` : '';
        const classes =
          typeof element.className === 'string'
            ? element.className
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((name) => `.${name}`)
                .join('')
            : '';
        return `${tag}${id}${classes}`;
      };
      const textOf = (element: Element) =>
        (element.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 90);
      const visible = (element: Element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.display !== 'none' &&
          style.visibility !== 'hidden'
        );
      };

      const viewportWidth = window.innerWidth;
      const documentWidth = document.documentElement.scrollWidth;
      const outsideElements = [...document.querySelectorAll('body *')]
        .filter(visible)
        .map((element) => {
          const rect = element.getBoundingClientRect();
          let ancestor = element.parentElement;
          let insideScrollableRegion = false;
          while (ancestor && ancestor !== document.body) {
            const overflowX = getComputedStyle(ancestor).overflowX;
            if (overflowX === 'auto' || overflowX === 'scroll') {
              insideScrollableRegion = true;
              break;
            }
            ancestor = ancestor.parentElement;
          }
          return {
            element,
            tag: element.tagName.toLowerCase(),
            selector: describe(element),
            text: textOf(element),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            interactive:
              element.matches('button, a, input, select, textarea, [role="button"]'),
            expectedOverflow:
              insideScrollableRegion || Boolean(element.closest('[aria-hidden="true"]')),
          };
        })
        .filter(
          (item) => item.left < -2 || item.right > viewportWidth + 2,
        )
        .sort(
          (a, b) =>
            Math.max(Math.abs(a.left), a.right - viewportWidth) -
            Math.max(Math.abs(b.left), b.right - viewportWidth),
        )
        .slice(0, 20)
        .map(({ element: _element, ...item }) => item);

      const clippedText = [...document.querySelectorAll('body *')]
        .filter(visible)
        .filter((element) => {
          if (element.children.length > 0) return false;
          const style = getComputedStyle(element);
          const clips =
            style.overflowX === 'hidden' ||
            style.overflowX === 'clip' ||
            style.textOverflow === 'ellipsis';
          return clips && element.scrollWidth > element.clientWidth + 2;
        })
        .slice(0, 15)
        .map((element) => ({ selector: describe(element), text: textOf(element) }));

      const cardSelector =
        '.auth-card, .onboarding-card, .food-analyzer-panel, .nutrition-card, .feature-card, .journey-panel, .app-main .rounded-2xl, .app-main .rounded-3xl';
      const cards = [...document.querySelectorAll(cardSelector)]
        .filter(visible)
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            selector: describe(element),
            width: Math.round(rect.width),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
          };
        })
        .slice(0, 40);

      const images = [...document.querySelectorAll('img')]
        .filter(visible)
        .map((image) => {
          const rect = image.getBoundingClientRect();
          return {
            alt: image.alt || '(no alt text)',
            loaded: image.complete && image.naturalWidth > 0,
            settled: image.complete,
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            naturalWidth: image.naturalWidth,
            naturalHeight: image.naturalHeight,
            objectFit: getComputedStyle(image).objectFit,
          };
        })
        .slice(0, 30);

      const charts = [
        ...document.querySelectorAll(
          '.journey-chart, .nutrition-grid, .app-main svg, [role="img"][aria-label*="chart" i]',
        ),
      ]
        .filter(visible)
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            selector: describe(element),
            width: Math.round(rect.width),
            left: Math.round(rect.left),
            right: Math.round(rect.right),
          };
        })
        .slice(0, 30);

      const buttons = [...document.querySelectorAll('button')]
        .filter(visible)
        .map((button) => {
          const rect = button.getBoundingClientRect();
          return {
            selector: describe(button),
            text: textOf(button),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            disabled: (button as HTMLButtonElement).disabled,
          };
        });
      const forms = [...document.querySelectorAll('form')]
        .filter(visible)
        .map((form) =>
          [...form.querySelectorAll('input, select, textarea, button')].filter(
            visible,
          ),
        );
      const controls = forms.flat();
      const unusableControls = controls
        .map((control) => {
          const target =
            control.matches('input, select, textarea')
              ? control.closest('.auth-input-wrap') || control
              : control;
          const rect = target.getBoundingClientRect();
          return {
            selector: describe(control),
            text: textOf(control),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          };
        })
        .filter((control) => control.width < 40 || control.height < 32);
      const smallTargets = buttons.filter(
        (button) => button.width < 40 || button.height < 40,
      );

      const findings: Finding[] = [];
      if (documentWidth > window.innerWidth) {
        findings.push({
          level: 'FAIL',
          category: 'Horizontal overflow',
          detail: `Document width ${documentWidth}px exceeds viewport width ${window.innerWidth}px by ${documentWidth - window.innerWidth}px.`,
        });
      }
      const unexpectedOutsideElements = outsideElements.filter(
        (element) => !element.expectedOverflow,
      );
      if (unexpectedOutsideElements.some((element) => element.interactive)) {
        findings.push({
          level: 'FAIL',
          category: 'Interactive element outside viewport',
          detail: unexpectedOutsideElements
            .filter((element) => element.interactive)
            .map((element) => `${element.selector} (${element.left}..${element.right}px)`)
            .join('; '),
        });
      } else if (unexpectedOutsideElements.length > 0) {
        findings.push({
          level: 'WARN',
          category: 'Elements extend beyond viewport',
          detail: unexpectedOutsideElements
            .slice(0, 5)
            .map((element) => `${element.selector} (${element.left}..${element.right}px)`)
            .join('; '),
        });
      }
      if (clippedText.length > 0) {
        findings.push({
          level: 'WARN',
          category: 'Text clipping candidates',
          detail: clippedText
            .slice(0, 5)
            .map((item) => `${item.selector}: "${item.text}"`)
            .join('; '),
        });
      }
      const brokenImages = images.filter(
        (image) => image.settled && !image.loaded,
      );
      if (brokenImages.length > 0) {
        findings.push({
          level: 'FAIL',
          category: 'Images not loaded',
          detail: brokenImages.map((image) => image.alt).join(', '),
        });
      }
      const pendingImages = images.filter((image) => !image.settled);
      if (pendingImages.length > 0) {
        findings.push({
          level: 'WARN',
          category: 'Images still loading at capture',
          detail: `${pendingImages.length} visible image(s) had not settled before measurement.`,
        });
      }
      const outOfBoundsCharts = charts.filter(
        (chart) => chart.left < -2 || chart.right > viewportWidth + 2,
      );
      if (outOfBoundsCharts.length > 0) {
        findings.push({
          level: 'FAIL',
          category: 'Chart outside viewport',
          detail: outOfBoundsCharts.map((chart) => chart.selector).join(', '),
        });
      }
      if (smallTargets.length > 0) {
        findings.push({
          level: 'WARN',
          category: 'Small button targets',
          detail: smallTargets
            .slice(0, 8)
            .map((button) => `${button.selector} "${button.text}" (${button.width}×${button.height}px)`)
            .join('; '),
        });
      }
      if (unusableControls.length > 0) {
        findings.push({
          level: 'WARN',
          category: 'Small form controls',
          detail: unusableControls
            .slice(0, 8)
            .map((control) => `${control.selector} "${control.text}" (${control.width}×${control.height}px)`)
            .join('; '),
        });
      }

      return {
        screen,
        width,
        height,
        documentWidth,
        horizontalOverflow: Math.max(0, documentWidth - window.innerWidth),
        outsideElements,
        clippedText,
        cards,
        images,
        charts,
        buttons: {
          count: buttons.length,
          smallTargets,
          disabled: buttons.filter((button) => button.disabled).length,
        },
        forms: {
          count: forms.length,
          controls: controls.length,
          unusableControls,
        },
        findings,
      };
    },
    { screen, width: await page.evaluate(() => window.innerWidth), height: await page.evaluate(() => window.innerHeight) },
  );
}

function markdownTable(rows: string[][]) {
  if (rows.length === 0) return '_None._';
  const [header, ...body] = rows;
  return [
    `| ${header.join(' | ')} |`,
    `| ${header.map(() => '---').join(' | ')} |`,
    ...body.map((row) => `| ${row.join(' | ')} |`),
  ].join('\n');
}

test('mobile responsive audit across requested viewports', async ({ page }) => {
  test.setTimeout(180_000);
  const outputDirectory = join(process.cwd(), 'mobile-test-results');
  const screenshotsDirectory = join(outputDirectory, 'screenshots');
  await mkdir(screenshotsDirectory, { recursive: true });

  const audit: ViewportAudit[] = [];
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('requestfailed', (request) => {
    failedRequests.push(
      `${request.method()} ${request.url()} — ${request.failure()?.errorText || 'request failed'}`,
    );
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      failedRequests.push(`${response.status()} ${response.url()}`);
    }
  });

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    const viewportAudit: ViewportAudit = {
      ...viewport,
      screens: [],
      consoleErrors: [],
      pageErrors: [],
      failedRequests: [],
    };
    const consoleStart = consoleErrors.length;
    const pageErrorStart = pageErrors.length;
    const requestStart = failedRequests.length;

    const capture = async (screen: string) => {
      await page.evaluate(() => {
        document.querySelectorAll('img').forEach((image) => {
          image.loading = 'eager';
        });
      });
      await page.evaluate(async () => {
        const imageDecodes = [...document.images].map((image) =>
          image.decode().then(
            () => undefined,
            () => undefined,
          ),
        );
        await Promise.race([
          Promise.all(imageDecodes),
          new Promise<void>((resolve) => window.setTimeout(resolve, 4000)),
        ]);
      });
      if (screen === 'home') {
        const pageHeight = await page.evaluate(() => document.documentElement.scrollHeight);
        const scrollStep = await page.evaluate(() => window.innerHeight);
        for (let scrollY = 0; scrollY < pageHeight; scrollY += scrollStep) {
          await page.evaluate((y) => window.scrollTo(0, y), scrollY);
          await page.waitForTimeout(120);
        }
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(700);
      }
      await page.waitForTimeout(100);
      const fileName = `${viewport.width}x${viewport.height}-${screen}.png`;
      await page.screenshot({
        path: join(screenshotsDirectory, fileName),
        fullPage: true,
        animations: 'disabled',
      });
      const result = await auditScreen(page, screen);
      viewportAudit.screens.push(result);
    };

    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await capture('login');

    await page.getByRole('tab', { name: 'Sign Up' }).click();
    await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    await capture('signup');
    await page.getByRole('tab', { name: 'Login' }).click();
    await expect(page.locator('input[name="confirm-password"]')).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'Email address' })).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Login' })).toBeEnabled();

    await page.getByRole('button', { name: 'Explore in demo mode' }).click();
    await expect(page.locator('.landing-page')).toBeVisible();
    await capture('home');

    await page.getByRole('button', { name: 'Open navigation menu' }).click();
    await expect(page.getByRole('navigation', { name: 'Mobile navigation' })).toBeVisible();
    await capture('home-menu-open');
    await page.getByRole('button', { name: 'Close navigation menu' }).click();
    await expect(page.getByRole('navigation', { name: 'Mobile navigation' })).toBeHidden();

    const navigate = async (name: string) => {
      await page.getByRole('button', { name: 'Open navigation menu' }).click();
      const menu = page.getByRole('navigation', { name: 'Mobile navigation' });
      await expect(menu).toBeVisible();
      await menu.getByRole('button', { name, exact: true }).click();
      await expect(menu).toBeHidden();
    };

    await navigate('Analyze food');
    await expect(page.getByRole('heading', { name: 'Analyze Your Meal' })).toBeVisible();
    await capture('analyzer-upload');
    await page.getByRole('button', { name: /Take a Photo/ }).click();
    await expect(page.getByRole('heading', { name: 'Smart Camera Viewfinder' })).toBeVisible();
    await capture('analyzer-camera');
    await page.getByRole('button', { name: /Enter Food Manually/ }).click();
    await expect(page.getByRole('textbox', { name: /Search Indian or global dish/ })).toBeVisible();
    await page.getByRole('textbox', { name: /Search Indian or global dish/ }).fill('Paneer');
    await expect(
      page.locator('.food-analyzer-input-panel').getByRole('heading', { name: 'Paneer Rice Bowl' }),
    ).toBeVisible();
    await page.getByRole('textbox', { name: /Search Indian or global dish/ }).clear();
    await capture('analyzer-manual');

    await page.getByRole('button', { name: /Analyze Nutritional Value/ }).click();
    await expect(page.getByRole('button', { name: 'Analyze Another Meal' })).toBeVisible({
      timeout: 10_000,
    });
    await capture('results');

    await navigate('Nutrition journey');
    await expect(page.getByRole('heading', { name: "Today's Nutrition" })).toBeVisible();
    await capture('daily-dashboard');
    await page.getByRole('button', { name: 'Log Meal Manually' }).click();
    await expect(page.getByRole('heading', { name: 'Log Meal Entry' })).toBeVisible();
    await capture('daily-add-modal');
    await expect(page.getByRole('textbox', { name: 'e.g. Mixed Dal with 2 Rotis' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Save Entry' })).toBeEnabled();
    await page.getByRole('button', { name: 'Cancel' }).click();

    await navigate('Profile & goals');
    await expect(page.getByRole('heading', { name: 'Personal Nutrition Profile' })).toBeVisible();
    await capture('profile');

    viewportAudit.consoleErrors = consoleErrors.slice(consoleStart);
    viewportAudit.pageErrors = pageErrors.slice(pageErrorStart);
    viewportAudit.failedRequests = failedRequests.slice(requestStart);
    audit.push(viewportAudit);
  }

  const allScreens = audit.flatMap((viewport) => viewport.screens);
  const allFindings = allScreens.flatMap((screen) =>
    screen.findings.map((finding) => ({ ...finding, screen, width: screen.width })),
  );
  const failures = allFindings.filter((finding) => finding.level === 'FAIL');
  const warnings = allFindings.filter((finding) => finding.level === 'WARN');
  const allConsoleErrors = audit.flatMap((viewport) => viewport.consoleErrors);
  const allPageErrors = audit.flatMap((viewport) => viewport.pageErrors);
  const allFailedRequests = audit.flatMap((viewport) => viewport.failedRequests);

  const summaryRows = audit.map((viewport) => {
    const screens = viewport.screens;
    const overflows = screens.filter((screen) => screen.horizontalOverflow > 0).length;
    const screenFailures = screens.reduce(
      (count, screen) =>
        count + screen.findings.filter((finding) => finding.level === 'FAIL').length,
      0,
    );
    const screenWarnings = screens.reduce(
      (count, screen) =>
        count + screen.findings.filter((finding) => finding.level === 'WARN').length,
      0,
    );
    return [
      `${viewport.width}×${viewport.height}`,
      `${screens.length}`,
      `${overflows}`,
      `${screenFailures}`,
      `${screenWarnings}`,
      `${screens.reduce((count, screen) => count + screen.images.length, 0)}`,
      `${screens.reduce((count, screen) => count + screen.charts.length, 0)}`,
    ];
  });

  const findingRows = allFindings.map((finding) => [
    finding.level,
    `${finding.width}px`,
    finding.screen.screen,
    finding.category,
    finding.detail.replace(/\|/g, '\\|'),
  ]);
  const errorSection = (items: string[]) =>
    items.length ? items.map((item) => `- \`${item.replace(/`/g, "'")}\``).join('\n') : '_None._';
  const screenshotRows = allScreens.map(
    (screen) =>
      `- [${screen.width}×${screen.height} ${screen.screen}](./screenshots/${screen.width}x${screen.height}-${screen.screen}.png)`,
  );

  const report = `# NutriAI Mobile Responsive Test Report

Generated: ${new Date().toISOString()}

## Scope and method

- Browser: Playwright Chromium.
- Viewports: ${viewports.map(({ width, height }) => `${width}×${height}`).join(', ')}.
- Routes: \`/login\` and \`/\`; the root app’s accessible tab views were exercised through its navigation (Home, Analyze food, Smart analysis/results, Nutrition journey, and Profile & goals).
- Additional states: signup form, open mobile menu, camera and manual analyzer modes, manual-meal dialog.
- Screenshots: full-page captures for each listed state and viewport, saved under \`mobile-test-results/screenshots/\`. The landing page is scrolled through before capture so its in-view animations are visible.
- Responsive UI and audit updates were applied; no backend or data integrations were changed.

## Summary

${markdownTable([
  ['Viewport', 'Screens checked', 'Overflow screens', 'Actual UI failures', 'Warnings', 'Images inspected', 'Charts inspected'],
  ...summaryRows,
])}

- **Actual UI failures:** ${failures.length}
- **Warnings:** ${warnings.length}
- **Browser console errors:** ${allConsoleErrors.length}
- **Uncaught page errors:** ${allPageErrors.length}
- **Failed/HTTP-error network requests:** ${allFailedRequests.length}

### Failure vs. warning criteria

- **FAIL** means the document horizontally overflows, an interactive control falls outside the viewport, a displayed image fails to load, or a chart falls outside the viewport.
- **WARN** means content extends outside the viewport without an identified displaced control, text may be clipped, or a button/form control is smaller than the audit’s touch-target heuristic. Warnings require visual/contextual review; intentional image cropping and decorative effects are not automatically treated as failures.
- Passing an interaction confirms the element could be operated by Playwright, not that every assistive-technology or physical-device behavior has been validated.

## Findings

${markdownTable([['Level', 'Viewport', 'Screen', 'Category', 'Details'], ...findingRows])}

## Before/after comparison

- Baseline screenshots: \`mobile-test-results/baseline-screenshots/\` (55 captures).
- Updated screenshots: \`mobile-test-results/screenshots/\` (55 captures).
- Baseline report: \`mobile-test-results/responsive-report-before-fixes.md\`.
- The baseline recorded 0 actual UI failures and 80 heuristic warnings. The landing-page captures did not trigger scroll-reveal animations, and analyzer preset names were ellipsized. The updated captures trigger those reveals and show preset names on up to two lines.
- The updated findings below distinguish any remaining sizing heuristics from overflow or functional failures.

## Layout and control checks

Each screen audit recorded element bounds outside the viewport, text clipping candidates, card bounds, image display/natural dimensions and \`object-fit\`, chart/SVG container bounds, and visible button/form-control counts and sizes. Full-page screenshots show the rendered layout for visual review.

## Browser console errors

${errorSection(allConsoleErrors)}

## Uncaught page errors

${errorSection(allPageErrors)}

## Failed or HTTP-error network requests

${errorSection(allFailedRequests)}

## Screenshots

${screenshotRows.join('\n')}
`;

  await writeFile(join(outputDirectory, 'responsive-report.md'), report, 'utf8');

  expect(failures, 'no responsive UI failures were found').toEqual([]);
  console.log(
    JSON.stringify(
      {
        report: join(outputDirectory, 'responsive-report.md'),
        screenshotsDirectory,
        viewports: audit.map(({ width, height, screens }) => ({
          width,
          height,
          screens: screens.length,
          failures: screens.reduce(
            (count, screen) =>
              count + screen.findings.filter((finding) => finding.level === 'FAIL').length,
            0,
          ),
          warnings: screens.reduce(
            (count, screen) =>
              count + screen.findings.filter((finding) => finding.level === 'WARN').length,
            0,
          ),
        })),
        consoleErrors: allConsoleErrors.length,
        pageErrors: allPageErrors.length,
        failedRequests: allFailedRequests.length,
      },
      null,
      2,
    ),
  );

  expect(allPageErrors, 'no uncaught browser page errors').toEqual([]);
});
