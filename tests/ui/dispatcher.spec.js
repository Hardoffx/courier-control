const { test, expect } = require('./fixtures');

const pages = [
  ['/dispatcher/', 'dashboard'],
  ['/dispatcher/deliveries/', 'deliveries'],
  ['/dispatcher/stats/', 'statistics'],
  ['/dispatcher/couriers/new/', 'courier-create'],
  ['/dispatcher/couriers/', 'couriers'],
  ['/dispatcher/points/', 'points'],
  ['/dispatcher/routes/new/', 'route-create'],
  ['/dispatcher/ui-preview/', 'ui-preview'],
];

async function layoutViolations(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const nodes = [...document.querySelectorAll('input,select,textarea,button,.btn,form')];
    const issues = [];

    const isActuallyVisible = (el) => {
      if (el.closest('[hidden]')) return false;
      const closedDetails = el.closest('details:not([open])');
      if (closedDetails) {
        const summary = closedDetails.querySelector(':scope > summary');
        if (!summary || !summary.contains(el)) return false;
      }
      for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
        const style = getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden' ||
            style.visibility === 'collapse' || Number(style.opacity || 1) <= 0) {
          return false;
        }
      }
      return true;
    };

    for (const el of nodes) {
      if (!isActuallyVisible(el)) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (r.left < -1 || r.right > vw + 1) {
        issues.push({
          problem: 'viewport-overflow',
          tag: el.tagName,
          cls: el.className || '',
          left: Math.round(r.left),
          right: Math.round(r.right),
          viewport: vw,
        });
      }
    }

    const controls = [...document.querySelectorAll(
      'input:not([type="hidden"]),select,textarea,button,a.btn,summary.btn'
    )].filter((el) => {
      const r = el.getBoundingClientRect();
      return isActuallyVisible(el) && r.width > 1 && r.height > 1;
    });

    for (let i = 0; i < controls.length; i += 1) {
      const a = controls[i];
      const ar = a.getBoundingClientRect();
      for (let j = i + 1; j < controls.length; j += 1) {
        const b = controls[j];
        if (a.contains(b) || b.contains(a)) continue;
        const br = b.getBoundingClientRect();
        const overlapX = Math.min(ar.right, br.right) - Math.max(ar.left, br.left);
        const overlapY = Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top);
        if (overlapX > 3 && overlapY > 3) {
          issues.push({
            problem: 'interactive-overlap',
            a: a.tagName + '.' + (a.className || ''),
            b: b.tagName + '.' + (b.className || ''),
            overlapX: Math.round(overlapX),
            overlapY: Math.round(overlapY),
          });
        }
      }
    }
    return issues;
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


test('route-editor: responsive geometry', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/routes/910001/');
  await expect(page.locator('#template-route-editor-workspace')).toBeVisible();
  expect(await layoutViolations(page)).toEqual([]);

  const firstItem = page.locator('#template-route-editor-workspace .route-editor-item').first();
  await firstItem.locator(':scope > .editor-summary').click();
  await expect(firstItem).toHaveAttribute('open', '');
  await expect.poll(() => firstItem.evaluate((el) => el.style.height)).toBe('');
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await layoutViolations(page)).toEqual([]);

  const doc = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(doc.scrollWidth).toBeLessThanOrEqual(doc.clientWidth + 1);
});

test('route-run: responsive geometry', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/runs/910001/');
  await expect(page.locator('#run-live-workspace')).toBeVisible();
  expect(await layoutViolations(page)).toEqual([]);

  const firstItem = page.locator('#run-live-workspace .route-editor-item').first();
  await firstItem.locator(':scope > .editor-summary').click();
  await expect(firstItem).toHaveAttribute('open', '');
  await expect.poll(() => firstItem.evaluate((el) => el.style.height)).toBe('');
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await layoutViolations(page)).toEqual([]);

  const doc = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(doc.scrollWidth).toBeLessThanOrEqual(doc.clientWidth + 1);
});

test('deliveries: search and quick filters do not reload the document', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/deliveries/');
  await page.evaluate(() => { window.__deliveryWorkspaceMarker = 'alive'; });

  const search = page.locator('.delivery-filter-card input[name="q"]');
  await search.fill('needle');
  await expect(page).toHaveURL(/q=needle/);
  expect(await page.evaluate(() => window.__deliveryWorkspaceMarker)).toBe('alive');

  await page.locator('.delivery-quick a[href*="status=problem"]').click();
  await expect(page).toHaveURL(/status=problem/);
  expect(await page.evaluate(() => window.__deliveryWorkspaceMarker)).toBe('alive');
});



test('dashboard day navigation stays in the same document', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/');
  await page.evaluate(() => { window.__liveDayMarker = 'alive'; });
  await page.locator('[data-live-day]').first().click();
  await expect(page.locator('#dispatcher-day-workspace')).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__liveDayMarker || '')).toBe('alive');
});

test('delivery day navigation stays in the same document', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/deliveries/');
  await page.evaluate(() => { window.__liveDayMarker = 'alive'; });
  await page.locator('[data-live-delivery-date]').first().click();
  await expect(page.locator('.deliveries-workspace')).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__liveDayMarker || '')).toBe('alive');
});


test('route-editor: inline edit saves without document reload', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'single mutating smoke profile');
  await page.goto('/dispatcher/routes/910001/');
  await page.evaluate(() => { window.__routeEditorMarker = 'alive'; });

  const firstItem = page.locator('#template-route-editor-workspace .route-editor-item').first();
  await firstItem.locator(':scope > .editor-summary').click();
  const comment = firstItem.locator('.inline-edit-form input[name="comment"]');
  await comment.fill('Browser template note');
  const save = firstItem.locator('.inline-edit-form .save-inline');
  await expect(save).toBeVisible();
  await save.click();

  await expect.poll(() => page.evaluate(() => window.__routeEditorMarker || '')).toBe('alive');
  await expect(firstItem.locator('.meta-comment')).toContainText('Browser template note');

  await page.reload();
  const persisted = page.locator('#template-route-editor-workspace .route-editor-item').first();
  await persisted.locator(':scope > .editor-summary').click();
  await expect(persisted.locator('.inline-edit-form input[name="comment"]')).toHaveValue('Browser template note');
});

test('route-run: inline edit saves without document reload', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'single mutating smoke profile');
  await page.goto('/dispatcher/runs/910001/');
  await page.evaluate(() => { window.__routeRunMarker = 'alive'; });

  const firstItem = page.locator('#run-live-workspace .route-editor-item').first();
  await firstItem.locator(':scope > .editor-summary').click();
  const comment = firstItem.locator('.inline-edit-form input[name="comment"]');
  await comment.fill('Browser run note');
  const save = firstItem.locator('.inline-edit-form .save-inline');
  await expect(save).toBeVisible();
  await save.click();

  await expect.poll(() => page.evaluate(() => window.__routeRunMarker || '')).toBe('alive');
  await expect(firstItem.locator('.meta-comment')).toContainText('Browser run note');

  await page.reload();
  const persisted = page.locator('#run-live-workspace .route-editor-item').first();
  await persisted.locator(':scope > .editor-summary').click();
  await expect(persisted.locator('.inline-edit-form input[name="comment"]')).toHaveValue('Browser run note');
});


test('couriers: mobile card is compact and expandable', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'mobile accordion behavior');
  await page.goto('/dispatcher/couriers/');
  const card = page.locator('[data-courier-card]').first();
  await expect(card).toBeVisible();
  await expect(card).not.toHaveAttribute('open', '');

  const body = card.locator('.courier-card-body');
  await expect(body).not.toBeVisible();
  await card.locator(':scope > summary').click();
  await expect(card).toHaveAttribute('open', '');
  await expect(body).toBeVisible();
});

test('courier preview: date controls stay inside mobile card', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'mobile preview geometry');
  await page.goto('/dispatcher/couriers/');
  const href = await page.locator('a[href*="/dispatcher/couriers/"][href*="/preview/"]').first().getAttribute('href');
  expect(href).toBeTruthy();
  await page.goto(href);
  const form = page.locator('.preview-live-date');
  await expect(form).toBeVisible();

  const geometry = await form.evaluate((el) => {
    const card = el.closest('.card').getBoundingClientRect();
    const formRect = el.getBoundingClientRect();
    const input = el.querySelector('input[type="date"]').getBoundingClientRect();
    const button = el.querySelector('.btn').getBoundingClientRect();
    return {
      cardLeft: card.left,
      cardRight: card.right,
      formLeft: formRect.left,
      formRight: formRect.right,
      inputLeft: input.left,
      inputRight: input.right,
      buttonLeft: button.left,
      buttonRight: button.right,
      gap: button.top - input.bottom,
    };
  });
  expect(geometry.formLeft).toBeGreaterThanOrEqual(geometry.cardLeft - 1);
  expect(geometry.formRight).toBeLessThanOrEqual(geometry.cardRight + 1);
  expect(geometry.inputLeft).toBeGreaterThanOrEqual(geometry.cardLeft - 1);
  expect(geometry.inputRight).toBeLessThanOrEqual(geometry.cardRight + 1);
  expect(geometry.buttonLeft).toBeGreaterThanOrEqual(geometry.cardLeft - 1);
  expect(geometry.buttonRight).toBeLessThanOrEqual(geometry.cardRight + 1);
  expect(geometry.gap).toBeGreaterThanOrEqual(8);
});

test('route-run: phone KPI cards stay an equal 2x2 grid', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'phone KPI geometry');
  await page.goto('/dispatcher/runs/910001/');
  const cards = page.locator('.route-kpi-grid .kpi');
  await expect(cards).toHaveCount(4);
  const geometry = await cards.evaluateAll((nodes) => nodes.map((el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, right: r.right };
  }));
  const widths = geometry.map((item) => item.width);
  expect(Math.max(...widths) - Math.min(...widths)).toBeLessThanOrEqual(2);
  expect(Math.abs(geometry[0].top - geometry[1].top)).toBeLessThanOrEqual(2);
  expect(Math.abs(geometry[2].top - geometry[3].top)).toBeLessThanOrEqual(2);
  expect(geometry[0].right).toBeLessThanOrEqual(page.viewportSize().width + 1);
  expect(geometry[1].right).toBeLessThanOrEqual(page.viewportSize().width + 1);
});
