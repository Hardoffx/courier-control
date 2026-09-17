const { test: base, expect } = require('@playwright/test');

const test = base.extend({
  dispatcherPage: async ({ page }, use) => {
    await page.goto('/login/');
    await page.locator('input[name="username"]').fill('ui_dispatcher');
    await page.locator('input[name="password"]').fill('ui-test-only-password');
    await Promise.all([
      page.waitForURL(/\/dispatcher\//),
      page.locator('button[type="submit"], input[type="submit"]').click(),
    ]);
    await use(page);
  },
});

module.exports = { test, expect };
