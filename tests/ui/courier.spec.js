const { test, expect } = require('@playwright/test');

async function loginCourier(page) {
  await page.goto('/login/');
  await page.locator('input[name="username"]').fill('ui_courier');
  await page.locator('input[name="password"]').fill('ui-test-only-password');
  await Promise.all([
    page.waitForURL(/\/courier\//),
    page.locator('button[type="submit"], input[type="submit"]').click(),
  ]);
}

test('courier note saves without document reload', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'single mutating smoke profile');
  await loginCourier(page);
  await expect(page.locator('#top')).toBeVisible();
  await page.evaluate(() => { window.__courierLiveMarker = 'alive'; });

  const editor = page.locator('.selected-note-editor');
  await editor.locator('summary').click();
  const input = editor.locator('input[name="courier_daily_note"]');
  await input.fill('UI live note');
  await editor.locator('button[type="submit"]').click();

  await expect.poll(() => page.evaluate(() => window.__courierLiveMarker || '')).toBe('alive');
  await expect(page.locator('#top')).toContainText('UI live note');
  await expect(page.locator('.selected-note-editor summary')).toContainText('Изменить заметку');
});


test('long route stays dense on target phone widths', async ({ page }, testInfo) => {
  const targetProjects = new Set(['mobile-375', 'iphone-webkit', 'mobile-430']);
  test.skip(!targetProjects.has(testInfo.project.name), '375/390/430 density QA only');

  await loginCourier(page);
  await expect(page.locator('#top')).toBeVisible();
  await expect(page.locator('.route-title .muted')).toContainText('32 точек');

  const rows = page.locator('#route-list > .route-list > .route-item');
  await expect(rows).toHaveCount(37);

  const metrics = await page.evaluate(() => {
    const routeRows = [...document.querySelectorAll('#route-list > .route-list > .route-item > .route-row')].slice(0, 32);
    const heights = routeRows.map((row) => row.getBoundingClientRect().height);
    return {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      minHeight: Math.min(...heights),
      maxHeight: Math.max(...heights),
      count: routeRows.length,
    };
  });

  expect(metrics.count).toBe(32);
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
  expect(metrics.minHeight).toBeGreaterThanOrEqual(44);
  expect(metrics.maxHeight).toBeLessThan(120);

  const lastLongStop = rows.nth(31);
  await lastLongStop.scrollIntoViewIfNeeded();
  await lastLongStop.locator(':scope > .route-row').click();
  await expect(lastLongStop).toHaveAttribute('open', '');
  await expect(lastLongStop.locator('.compact-top-actions')).toBeVisible();

  const right = await lastLongStop.evaluate((el) => el.getBoundingClientRect().right);
  const viewport = await page.evaluate(() => document.documentElement.clientWidth);
  expect(right).toBeLessThanOrEqual(viewport + 1);
});
