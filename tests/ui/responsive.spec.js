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
    const result = await page.evaluate(() => {
      const controls = [...document.querySelectorAll('input:not([type="hidden"]),button')].filter((el) => {
        const r = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return r.width > 1 && r.height > 1 && style.display !== 'none' && style.visibility !== 'hidden';
      });
      const overlaps = [];
      for (let i = 0; i < controls.length; i += 1) {
        const ar = controls[i].getBoundingClientRect();
        for (let j = i + 1; j < controls.length; j += 1) {
          const br = controls[j].getBoundingClientRect();
          const x = Math.min(ar.right, br.right) - Math.max(ar.left, br.left);
          const y = Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top);
          if (x > 3 && y > 3) overlaps.push({
            a: controls[i].tagName + '.' + (controls[i].className || ''),
            b: controls[j].tagName + '.' + (controls[j].className || ''),
            x: Math.round(x),
            y: Math.round(y),
          });
        }
      }
      return { count: controls.length, overlaps };
    });
    expect(result.count).toBeGreaterThan(1);
    expect(result.overlaps).toEqual([]);
  });
}
