# NutriAI Mobile Responsive Test Report

Generated: 2026-11-11T17:19:48.973Z

## Scope and method

- Browser: Playwright Chromium.
- Viewports: 360×800, 375×812, 390×844, 414×896, 430×932.
- Routes: `/login` and `/`; the root app’s accessible tab views were exercised through its navigation (Home, Analyze food, Smart analysis/results, Nutrition journey, and Profile & goals).
- Additional states: signup form, open mobile menu, camera and manual analyzer modes, manual-meal dialog.
- Screenshots: full-page captures for each listed state and viewport, saved under `mobile-test-results/screenshots/`. The landing page is scrolled through before capture so its in-view animations are visible.
- Responsive UI and audit updates were applied; no backend or data integrations were changed.

## Summary

| Viewport | Screens checked | Overflow screens | Actual UI failures | Warnings | Images inspected | Charts inspected |
| --- | --- | --- | --- | --- | --- | --- |
| 360×800 | 11 | 0 | 0 | 0 | 31 | 135 |
| 375×812 | 11 | 0 | 0 | 0 | 31 | 135 |
| 390×844 | 11 | 0 | 0 | 0 | 31 | 135 |
| 414×896 | 11 | 0 | 0 | 0 | 31 | 135 |
| 430×932 | 11 | 0 | 0 | 0 | 31 | 135 |

- **Actual UI failures:** 0
- **Warnings:** 0
- **Browser console errors:** 0
- **Uncaught page errors:** 0
- **Failed/HTTP-error network requests:** 0

### Failure vs. warning criteria

- **FAIL** means the document horizontally overflows, an interactive control falls outside the viewport, a displayed image fails to load, or a chart falls outside the viewport.
- **WARN** means content extends outside the viewport without an identified displaced control, text may be clipped, or a button/form control is smaller than the audit’s touch-target heuristic. Warnings require visual/contextual review; intentional image cropping and decorative effects are not automatically treated as failures.
- Passing an interaction confirms the element could be operated by Playwright, not that every assistive-technology or physical-device behavior has been validated.

## Findings

| Level | Viewport | Screen | Category | Details |
| --- | --- | --- | --- | --- |

## Before/after comparison

- Baseline screenshots: `mobile-test-results/baseline-screenshots/` (55 captures).
- Updated screenshots: `mobile-test-results/screenshots/` (55 captures).
- Baseline report: `mobile-test-results/responsive-report-before-fixes.md`.
- The baseline recorded 0 actual UI failures and 80 heuristic warnings. The landing-page captures did not trigger scroll-reveal animations, and analyzer preset names were ellipsized. The updated captures trigger those reveals and show preset names on up to two lines.
- The updated findings below distinguish any remaining sizing heuristics from overflow or functional failures.

## Layout and control checks

Each screen audit recorded element bounds outside the viewport, text clipping candidates, card bounds, image display/natural dimensions and `object-fit`, chart/SVG container bounds, and visible button/form-control counts and sizes. Full-page screenshots show the rendered layout for visual review.

## Browser console errors

_None._

## Uncaught page errors

_None._

## Failed or HTTP-error network requests

_None._

## Screenshots

- [360×800 login](./screenshots/360x800-login.png)
- [360×800 signup](./screenshots/360x800-signup.png)
- [360×800 home](./screenshots/360x800-home.png)
- [360×800 home-menu-open](./screenshots/360x800-home-menu-open.png)
- [360×800 analyzer-upload](./screenshots/360x800-analyzer-upload.png)
- [360×800 analyzer-camera](./screenshots/360x800-analyzer-camera.png)
- [360×800 analyzer-manual](./screenshots/360x800-analyzer-manual.png)
- [360×800 results](./screenshots/360x800-results.png)
- [360×800 daily-dashboard](./screenshots/360x800-daily-dashboard.png)
- [360×800 daily-add-modal](./screenshots/360x800-daily-add-modal.png)
- [360×800 profile](./screenshots/360x800-profile.png)
- [375×812 login](./screenshots/375x812-login.png)
- [375×812 signup](./screenshots/375x812-signup.png)
- [375×812 home](./screenshots/375x812-home.png)
- [375×812 home-menu-open](./screenshots/375x812-home-menu-open.png)
- [375×812 analyzer-upload](./screenshots/375x812-analyzer-upload.png)
- [375×812 analyzer-camera](./screenshots/375x812-analyzer-camera.png)
- [375×812 analyzer-manual](./screenshots/375x812-analyzer-manual.png)
- [375×812 results](./screenshots/375x812-results.png)
- [375×812 daily-dashboard](./screenshots/375x812-daily-dashboard.png)
- [375×812 daily-add-modal](./screenshots/375x812-daily-add-modal.png)
- [375×812 profile](./screenshots/375x812-profile.png)
- [390×844 login](./screenshots/390x844-login.png)
- [390×844 signup](./screenshots/390x844-signup.png)
- [390×844 home](./screenshots/390x844-home.png)
- [390×844 home-menu-open](./screenshots/390x844-home-menu-open.png)
- [390×844 analyzer-upload](./screenshots/390x844-analyzer-upload.png)
- [390×844 analyzer-camera](./screenshots/390x844-analyzer-camera.png)
- [390×844 analyzer-manual](./screenshots/390x844-analyzer-manual.png)
- [390×844 results](./screenshots/390x844-results.png)
- [390×844 daily-dashboard](./screenshots/390x844-daily-dashboard.png)
- [390×844 daily-add-modal](./screenshots/390x844-daily-add-modal.png)
- [390×844 profile](./screenshots/390x844-profile.png)
- [414×896 login](./screenshots/414x896-login.png)
- [414×896 signup](./screenshots/414x896-signup.png)
- [414×896 home](./screenshots/414x896-home.png)
- [414×896 home-menu-open](./screenshots/414x896-home-menu-open.png)
- [414×896 analyzer-upload](./screenshots/414x896-analyzer-upload.png)
- [414×896 analyzer-camera](./screenshots/414x896-analyzer-camera.png)
- [414×896 analyzer-manual](./screenshots/414x896-analyzer-manual.png)
- [414×896 results](./screenshots/414x896-results.png)
- [414×896 daily-dashboard](./screenshots/414x896-daily-dashboard.png)
- [414×896 daily-add-modal](./screenshots/414x896-daily-add-modal.png)
- [414×896 profile](./screenshots/414x896-profile.png)
- [430×932 login](./screenshots/430x932-login.png)
- [430×932 signup](./screenshots/430x932-signup.png)
- [430×932 home](./screenshots/430x932-home.png)
- [430×932 home-menu-open](./screenshots/430x932-home-menu-open.png)
- [430×932 analyzer-upload](./screenshots/430x932-analyzer-upload.png)
- [430×932 analyzer-camera](./screenshots/430x932-analyzer-camera.png)
- [430×932 analyzer-manual](./screenshots/430x932-analyzer-manual.png)
- [430×932 results](./screenshots/430x932-results.png)
- [430×932 daily-dashboard](./screenshots/430x932-daily-dashboard.png)
- [430×932 daily-add-modal](./screenshots/430x932-daily-add-modal.png)
- [430×932 profile](./screenshots/430x932-profile.png)
