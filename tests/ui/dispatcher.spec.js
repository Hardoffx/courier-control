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


test('route-editor: pencil edits address inline without page reload', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile-375', 'single mutating smoke profile');
  await page.goto('/dispatcher/routes/910001/');
  const card=page.locator('#template-route-editor-workspace .route-editor-item').first();
  const address=card.locator('.editor-address');
  const pencil=card.locator('.editor-address-pencil');
  const form=card.locator('.editor-address-inline');
  const original=(await address.textContent()).trim();
  await expect(pencil).toBeHidden();
  await expect(card.locator('.editor-body .point-address-form')).toHaveCount(1);
  await page.evaluate(() => { window.__inlineAddressMarker = 'alive'; });

  await card.locator(':scope > .editor-summary').click();
  await expect(card).toHaveAttribute('open', '');
  await expect(pencil).toBeVisible();
  await pencil.click();
  await expect(form).toBeVisible();
  await expect(card).toHaveAttribute('open', '');
  await expect(card.locator('.editor-address-row')).toBeVisible();
  expect(await layoutViolations(page)).toEqual([]);

  await form.locator('input[name="address"]').fill('Москва, ул Тестовая, д. 22');
  await form.locator('.editor-address-cancel').click();
  await expect(form).toBeHidden();
  await expect(address).toHaveText(original);

  await pencil.click();
  await form.locator('input[name="address"]').fill('Москва, ул Тестовая, д. 22');
  await form.locator('.editor-address-apply').click();
  await expect(form).toBeHidden();
  await expect(address).toHaveText('Москва, ул Тестовая 22');
  await expect.poll(() => page.evaluate(() => window.__inlineAddressMarker || '')).toBe('alive');
  await expect(card).toHaveAttribute('open', '');
  // A sticky header can cover scrolled-away controls without any layout overlap.
  // Check the complete document geometry from its natural top position.
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    window.scrollTo(0, 0);
  });
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  expect(await layoutViolations(page)).toEqual([]);
});

test('route-editor: pencil appears only while open and chevron does not shift', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/routes/910001/');
  const card=page.locator('#template-route-editor-workspace .route-editor-item').first();
  const summary=card.locator(':scope > .editor-summary');
  const pencil=card.locator('.editor-address-pencil');
  const editor=card.locator('.editor-address-inline');

  const geometry=()=>card.evaluate(el=>{
    const summary=el.querySelector(':scope > .editor-summary').getBoundingClientRect();
    const arrow=el.querySelector('.route-chevron').getBoundingClientRect();
    const address=el.querySelector('.editor-address').getBoundingClientRect();
    return {
      arrowX:arrow.left-summary.left,
      arrowY:arrow.top-summary.top,
      addressHeight:address.height,
      scrollWidth:document.documentElement.scrollWidth,
      viewportWidth:document.documentElement.clientWidth,
    };
  });

  await expect(pencil).toBeHidden();
  const closed=await geometry();
  await summary.click();
  await expect(card).toHaveAttribute('open', '');
  await expect.poll(()=>card.evaluate(el=>el.style.height)).toBe('');
  await expect(pencil).toBeVisible();
  const opened=await geometry();
  expect(Math.abs(opened.arrowX-closed.arrowX)).toBeLessThanOrEqual(1);
  expect(Math.abs(opened.arrowY-closed.arrowY)).toBeLessThanOrEqual(1);
  expect(Math.abs(opened.addressHeight-closed.addressHeight)).toBeLessThanOrEqual(1);

  await pencil.click();
  await expect(editor).toBeVisible();
  const editing=await geometry();
  expect(Math.abs(editing.arrowX-opened.arrowX)).toBeLessThanOrEqual(1);
  expect(Math.abs(editing.arrowY-opened.arrowY)).toBeLessThanOrEqual(1);
  expect(editing.scrollWidth).toBeLessThanOrEqual(editing.viewportWidth+1);

  await editor.locator('.editor-address-cancel').click();
  await expect(editor).toBeHidden();
  await summary.click();
  await expect(card).not.toHaveAttribute('open', '');
  await expect(pencil).toBeHidden();
});

test('route-editor: chevron remains up while expanded and down when closed', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(!['mobile-375','iphone-webkit'].includes(testInfo.project.name), 'mobile accordion state');
  await page.goto('/dispatcher/routes/910001/');
  const cards=page.locator('#template-route-editor-workspace .route-editor-item');
  const direction=async card=>card.locator('.route-chevron').evaluate(el=>{
    const style=getComputedStyle(el);
    const matrix=new DOMMatrixReadOnly(style.transform);
    return {
      angle:Math.round((Math.atan2(matrix.b,matrix.a)*180/Math.PI+360)%360),
      marginTop:Math.round(parseFloat(style.marginTop)),
    };
  });
  const assertClosed=async card=>{
    await expect(card).not.toHaveAttribute('open','');
    await expect.poll(async()=>direction(card)).toEqual({angle:45,marginTop:-4});
  };
  const assertOpen=async card=>{
    await expect(card).toHaveAttribute('open','');
    await expect.poll(async()=>direction(card),{timeout:10000}).toEqual({angle:225,marginTop:4});
    await expect.poll(()=>card.evaluate(el=>el.style.height)).toBe('');
    // Regression: the arrow must not snap back down once its animation is cleaned up.
    await expect(direction(card)).resolves.toEqual({angle:225,marginTop:4});
  };
  const first=cards.first();
  const second=cards.nth(1);
  await assertClosed(first);
  await first.locator(':scope > summary').click();
  await assertOpen(first);
  await first.locator(':scope > summary').click();
  await assertClosed(first);
  await first.locator(':scope > summary').click();
  await assertOpen(first);
  await second.locator(':scope > summary').click();
  await assertOpen(second);
  await assertClosed(first);
  await second.locator(':scope > summary').click();
  await assertClosed(second);
});

test('route-editor: fixed action columns on short and long addresses', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/routes/910002/');
  const cards=page.locator('#template-route-editor-workspace .route-editor-item');
  expect(await cards.count()).toBeGreaterThan(12);

  const measure=()=>cards.evaluateAll(elements=>elements.slice(0,12).map(card=>{
    const summary=card.querySelector(':scope > .editor-summary');
    const pencil=summary.querySelector(':scope > .editor-address-pencil');
    const arrow=summary.querySelector(':scope > .route-chevron');
    const rect=summary.getBoundingClientRect();
    const pen=pencil.getBoundingClientRect();
    const chevron=arrow.getBoundingClientRect();
    return {
      rightInset:rect.right-chevron.right,
      pencilCenter:pen.left+pen.width/2-rect.left,
      chevronCenter:chevron.left+chevron.width/2-rect.left,
      pencilVisible:getComputedStyle(pencil).visibility==='visible',
      address:summary.querySelector('.editor-address').textContent.trim(),
    };
  }));

  const closed=await measure();
  expect(new Set(closed.map(row=>row.address.length)).size).toBeGreaterThan(1);
  const base=closed[0];
  for(const row of closed){
    expect(row.pencilVisible).toBe(false);
    expect(Math.abs(row.pencilCenter-base.pencilCenter)).toBeLessThanOrEqual(2);
    expect(Math.abs(row.chevronCenter-base.chevronCenter)).toBeLessThanOrEqual(2);
    expect(row.rightInset).toBeGreaterThanOrEqual(18);
    expect(row.pencilCenter).toBeLessThan(row.chevronCenter-20);
  }

  const card=cards.first();
  await card.locator(':scope > .editor-summary').click();
  await expect(card).toHaveAttribute('open','');
  await expect.poll(()=>card.evaluate(el=>el.style.height)).toBe('');
  const opened=(await measure())[0];
  expect(opened.pencilVisible).toBe(true);
  expect(Math.abs(opened.pencilCenter-base.pencilCenter)).toBeLessThanOrEqual(2);
  expect(Math.abs(opened.chevronCenter-base.chevronCenter)).toBeLessThanOrEqual(2);

  await card.locator('.editor-address-pencil').click();
  await expect(card.locator('.editor-address-inline')).toBeVisible();
  const editing=(await measure())[0];
  expect(Math.abs(editing.pencilCenter-base.pencilCenter)).toBeLessThanOrEqual(2);
  expect(Math.abs(editing.chevronCenter-base.chevronCenter)).toBeLessThanOrEqual(2);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
});

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


test('dashboard: KPI icons sit in top-right accents and route actions share a 58/42 row', async ({ dispatcherPage: page }) => {
  await page.goto('/dispatcher/');
  const kpis=page.locator('.ops-kpi');
  await expect(kpis).toHaveCount(4);
  const kpiBoxes=await kpis.evaluateAll(cards=>cards.map(card=>{
    const outer=card.getBoundingClientRect();
    const icon=card.querySelector('.ops-kpi-icon').getBoundingClientRect();
    return {
      top:icon.top-outer.top,
      right:outer.right-icon.right,
      width:icon.width,
      height:icon.height,
    };
  }));
  for(const kpi of kpiBoxes){
    expect(kpi.top).toBeGreaterThanOrEqual(5);
    expect(kpi.top).toBeLessThanOrEqual(13);
    expect(kpi.right).toBeGreaterThanOrEqual(5);
    expect(kpi.right).toBeLessThanOrEqual(13);
    expect(kpi.width).toBeGreaterThanOrEqual(32);
    expect(kpi.height).toBeGreaterThanOrEqual(32);
  }

  const card=page.locator('.ops-route-card:has(.route-card-actions a.btn)').first();
  await expect(card).toBeVisible();
  const actions=card.locator('.route-card-actions > a.btn');
  await expect(actions).toHaveCount(2);
  const bounds=await actions.evaluateAll(els=>els.map(el=>{
    const r=el.getBoundingClientRect();
    return {left:r.left,top:r.top,width:r.width,height:r.height};
  }));
  const [open,preview]=bounds;
  expect(Math.abs(open.top-preview.top)).toBeLessThanOrEqual(1);
  expect(Math.abs(open.height-preview.height)).toBeLessThanOrEqual(1);
  expect(open.left+open.width).toBeLessThan(preview.left);
  expect(open.width/(open.width+preview.width)).toBeGreaterThan(0.54);
  expect(open.width/(open.width+preview.width)).toBeLessThan(0.62);
  expect(await layoutViolations(page)).toEqual([]);
});

test('mobile Safari: editable form controls meet the 16px no-focus-zoom threshold', async ({ dispatcherPage: page }, testInfo) => {
  test.skip(testInfo.project.name!=='iphone-webkit', 'iOS Safari input focus behavior');
  await page.goto('/dispatcher/routes/910001/');
  const controls=page.locator('#generate-route-form input[type="date"],#generate-route-form select');
  await expect(controls).toHaveCount(2);
  const result=await controls.evaluateAll(els=>els.map(el=>({
    fontSize:parseFloat(getComputedStyle(el).fontSize),
    kind:el.tagName.toLowerCase(),
  })));
  for(const field of result)expect(field.fontSize).toBeGreaterThanOrEqual(16);
  const viewport=await page.locator('meta[name="viewport"]').getAttribute('content');
  expect(viewport).not.toContain('maximum-scale');
  expect(viewport).not.toContain('user-scalable=no');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBe(true);
});
