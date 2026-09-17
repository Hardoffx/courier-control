const { test, expect } = require('./fixtures');

const targets = [
  ['/dispatcher/', 'dashboard'],
  ['/dispatcher/stats/', 'statistics'],
  ['/dispatcher/couriers/new/', 'courier-create'],
  ['/dispatcher/routes/new/', 'route-create'],
  ['/dispatcher/ui-preview/', 'ui-preview'],
];

for (const [path, name] of targets) {
  test(`${name}: visual snapshot`, async ({ dispatcherPage: page }) => {
    await page.goto(path);
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await expect(page.locator('body')).toBeVisible();
    await expect(page).toHaveScreenshot(`${name}.png`, {
      fullPage: true,
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
      maxDiffPixelRatio: 0.01,
    });
  });
}
