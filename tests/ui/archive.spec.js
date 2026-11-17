const { test, expect } = require('./fixtures');

async function activeCourierRow(page, username) {
  if (await page.locator('.courier-desktop').isVisible()) {
    return page.locator('.courier-desktop tbody tr').filter({hasText:username});
  }
  return page.locator('.courier-card').filter({hasText:username});
}

async function noPageOverflow(page) {
  const delta=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  expect(delta).toBeLessThanOrEqual(1);
}

test('dispatcher archives and restores route and courier with accessible history', async({dispatcherPage:page},testInfo)=>{
  const suffix=Date.now().toString(36)+Math.random().toString(36).slice(2,6);
  const routeName='Archive QA '+suffix;
  await page.goto('/dispatcher/routes/new/');
  await page.locator('input[name="name"]').fill(routeName);
  await page.locator('form button').filter({hasText:'Сохранить маршрут'}).click();
  await expect(page).toHaveURL(/\/dispatcher\/routes\/\d+\//);
  await page.goto('/dispatcher/routes/');
  let card=page.locator('.route-card').filter({hasText:routeName});
  await expect(card).toBeVisible();
  await card.locator('a').filter({hasText:'Настройки'}).click();
  await page.getByRole('button',{name:'Переместить в архив'}).click();
  await expect(page.locator('#route-archive-dialog')).toBeVisible();
  await page.locator('#route-archive-dialog input[name=reason]').fill('Тест архива');
  await page.locator('#route-archive-dialog button[type=submit]').click();
  await page.goto('/dispatcher/routes/?view=archive');
  card=page.locator('.route-card').filter({hasText:routeName});
  await expect(card).toContainText('Тест архива');
  await card.locator('a').filter({hasText:'История'}).click();
  await expect(page.getByText('История рейсов')).toBeVisible();
  await expect(page.locator('h1')).toContainText(routeName);
  await noPageOverflow(page);
  await page.screenshot({path:testInfo.outputPath('route-archive-mobile.png'),fullPage:true});
  await page.goto('/dispatcher/routes/?view=archive');
  card=page.locator('.route-card').filter({hasText:routeName});
  page.once('dialog',d=>d.accept());
  await card.locator('form[action$="/restore/"] button').click();
  await page.goto('/dispatcher/routes/');
  await expect(page.locator('.route-card').filter({hasText:routeName})).toBeVisible();

  const username='archive-ui-'+suffix;
  await page.goto('/dispatcher/couriers/new/');
  await page.locator('input[name="first_name"]').fill('Тестовый');
  await page.locator('input[name="last_name"]').fill('Архив');
  await page.locator('input[name="username"]').fill(username);
  await page.locator('input[name="password"]').fill('only-in-ui-test-123');
  await page.locator('form button').filter({hasText:'Сохранить курьера'}).click();
  await page.goto('/dispatcher/couriers/');
  let courier=await activeCourierRow(page,username);
  await expect(courier).toBeVisible();
  if (await courier.evaluate(el => el.tagName.toLowerCase() === 'details')) {
    await courier.locator('summary').click();
  }
  await courier.locator('a').filter({hasText:'Настройки'}).click();
  await page.getByRole('button',{name:'Переместить в архив'}).click();
  await expect(page.locator('#courier-archive-dialog')).toBeVisible();
  await page.locator('#courier-archive-dialog input[name=reason]').fill('Резерв больше не нужен');
  await page.locator('#courier-archive-dialog button[type=submit]').click();
  await page.goto('/dispatcher/couriers/?view=archive');
  courier=await activeCourierRow(page,username);
  await expect(courier).toContainText(username);
  await expect(courier).toContainText('Архив');
  await noPageOverflow(page);
  await page.screenshot({path:testInfo.outputPath('courier-archive-mobile.png'),fullPage:true});
  if (await courier.evaluate(el => el.tagName.toLowerCase() === 'details')) {
    await courier.locator('summary').click();
  }
  page.once('dialog',d=>d.accept());
  await courier.locator('form[action$="/restore/"] button').click();
  await page.goto('/dispatcher/couriers/');
  await expect(await activeCourierRow(page,username)).toBeVisible();
});

test('directory live search keeps the active input mounted after results update', async({dispatcherPage:page})=>{
  await page.goto('/dispatcher/points/');
  const search=page.locator('.point-live-filter input[name=q]');
  await search.focus();
  await page.evaluate(()=>{window.__directorySearchInput=document.querySelector('.point-live-filter input[name=q]')});
  await search.fill('105');
  await expect.poll(()=>page.evaluate(()=>location.search)).toContain('q=105');
  expect(await page.evaluate(()=>document.querySelector('.point-live-filter input[name=q]')===window.__directorySearchInput)).toBe(true);
  await expect(search).toBeFocused();
  await expect(search).toHaveValue('105');
});

test('route time interval picker applies times without resizing the field', async({dispatcherPage:page})=>{
  await page.goto('/dispatcher/routes/new/');
  await page.locator('input[name="name"]').fill('Time QA '+Date.now());
  await page.getByRole('button',{name:'Сохранить маршрут'}).click();
  const source=page.locator('.add-source-card').filter({hasText:'Создать новую точку'});
  await source.locator('summary').click();
  const time=source.locator('input[name=time_window]');
  const original=await time.boundingBox();
  await time.click();
  const picker=page.locator('.time-window-dialog');
  await expect(picker).toBeVisible();
  await picker.locator('input[name=start]').fill('12:00');
  await picker.locator('input[name=end]').fill('15:00');
  await picker.getByRole('button',{name:'Применить'}).click();
  await expect(picker).not.toBeVisible();
  await expect(time).toHaveValue('12:00-15:00');
  const after=await time.boundingBox();
  expect(Math.abs(after.width-original.width)).toBeLessThanOrEqual(1);
});

test('statistics date controls are separated and fit the viewport', async({dispatcherPage:page})=>{
  await page.goto('/dispatcher/stats/');
  const start=page.locator('.stats-date-box').nth(0);
  const end=page.locator('.stats-date-box').nth(1);
  const a=await start.boundingBox();
  const b=await end.boundingBox();
  expect(a).toBeTruthy();
  expect(b).toBeTruthy();
  expect(a.x+a.width).toBeLessThanOrEqual(b.x-2);
  expect(b.x+b.width).toBeLessThanOrEqual(page.viewportSize().width+1);
});
