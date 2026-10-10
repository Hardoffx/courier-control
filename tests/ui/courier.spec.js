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

test('courier route cards expose the page background in their gaps', async ({ page }) => {
  await loginCourier(page);
  const list = page.locator('#route-list > .route-list.route-accordion-list');
  const stops = list.locator(':scope > .route-item');
  await expect(stops.first()).toBeVisible();
  await expect(stops.nth(1)).toBeVisible();

  const appearance = await page.evaluate(() => {
    const listEl = document.querySelector('#route-list > .route-list.route-accordion-list');
    const cards = [...listEl.querySelectorAll(':scope > .route-item')];
    const first = cards[0].getBoundingClientRect();
    const second = cards[1].getBoundingClientRect();
    const listStyle = getComputedStyle(listEl);
    const cardStyle = getComputedStyle(cards[0]);
    const sectionStyle = getComputedStyle(listEl.parentElement);
    const pageStyle = getComputedStyle(document.body);
    return {
      listBackground: listStyle.backgroundColor,
      sectionBackground: sectionStyle.backgroundColor,
      pageBackground: pageStyle.backgroundColor,
      borderWidth: listStyle.borderTopWidth,
      boxShadow: listStyle.boxShadow,
      overflow: listStyle.overflow,
      cardBackground: cardStyle.backgroundColor,
      cardGap: second.top - first.bottom,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    };
  });

  expect(appearance.listBackground).toBe('rgba(0, 0, 0, 0)');
  expect(appearance.sectionBackground).toBe('rgba(0, 0, 0, 0)');
  expect(appearance.pageBackground).toBe('rgb(243, 246, 250)');
  expect(appearance.borderWidth).toBe('0px');
  expect(appearance.boxShadow).toBe('none');
  expect(appearance.overflow).toBe('visible');
  expect(appearance.cardBackground).toBe('rgb(255, 255, 255)');
  expect(appearance.cardGap).toBeGreaterThanOrEqual(5);
  expect(appearance.cardGap).toBeLessThanOrEqual(7);
  expect(appearance.scrollWidth).toBeLessThanOrEqual(appearance.clientWidth + 1);
});
