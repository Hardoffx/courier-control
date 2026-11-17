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
  await card.locator('input[name=reason]').fill('Тест архива');
  page.once('dialog',d=>d.accept());
  await card.locator('form[action$="/archive/"] button').click();
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
  await courier.locator('input[name=reason]').fill('Резерв больше не нужен');
  page.once('dialog',d=>d.accept());
  await courier.locator('form[action$="/archive/"] button').click();
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
