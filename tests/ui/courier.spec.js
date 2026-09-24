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

test('courier note saves without document reload', async ({ page }) => {
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
});
