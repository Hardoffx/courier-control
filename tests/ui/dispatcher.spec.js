const { test, expect } = require('./fixtures');

const pages = [
  ['/dispatcher/', 'dashboard'],
  ['/dispatcher/stats/', 'statistics'],
  ['/dispatcher/couriers/new/', 'courier-create'],
  ['/dispatcher/routes/new/', 'route-create'],
  ['/dispatcher/ui-preview/', 'ui-preview'],
];

async function layoutViolations(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const nodes = [...document.querySelectorAll('input,select,textarea,button,.btn,form')];
    return nodes.flatMap((el) => {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) return [];
      const problems = [];
      if (r.left < -1 || r.right > vw + 1) problems.push('viewport-overflow');
      return problems.map(problem => ({
        problem,
        tag: el.tagName,
        cls: el.className || '',
        left: Math.round(r.left),
        right: Math.round(r.right),
        viewport: vw,
      }));
    });
  });
}

for (const [path, name] of pages) {
  test(`${name}: responsive geometry`, async ({ dispatcherPage: page }) => {
    await page.goto(path);
    await expect(page.locator('body')).toBeVisible();
    expect(await layoutViolations(page)).toEqual([]);
    const doc = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(doc.scrollWidth).toBeLessThanOrEqual(doc.clientWidth + 1);
  });
}
