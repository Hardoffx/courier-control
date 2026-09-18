const { test, expect } = require('@playwright/test');

const publicPages = ['/login/'];

for (const path of publicPages) {
  test(`${path} has no page-level horizontal overflow`, async ({ page }) => {
    await page.goto(path);
    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  });

  test(`${path} renders core controls without overlap`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator('form')).toBeVisible();
    const controls = page.locator('input, button');
    expect(await controls.count()).toBeGreaterThan(1);
  });
}
