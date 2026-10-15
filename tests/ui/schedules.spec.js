const { test, expect } = require('./fixtures');

async function csrf(page){return page.locator('[name=csrfmiddlewaretoken]').first().inputValue();}
async function createCourier(page){
  const username='schedule-ui-'+Date.now()+'-'+Math.random().toString(36).slice(2,7);
  const response=await page.request.post('/dispatcher/couriers/new/',{form:{csrfmiddlewaretoken:await csrf(page),username,first_name:username,password:'local-ui-only-password',is_active:'on'}});
  expect(response.ok()).toBeTruthy();
  await page.goto('/dispatcher/couriers/');
  const href=await page.locator('.courier-desktop tr').filter({hasText:username}).locator('a[href$="/schedule/"]').getAttribute('href');
  return {username,href,id:Number(href.match(/couriers\/(\d+)/)[1])};
}
async function openSchedule(page,c,month='2032-02'){
  await page.goto(c.href+'?month='+month);
  await expect(page.locator('#schedule-feedback')).toHaveText('График обновлён');
}
async function day(page,date){await page.locator(`.schedule-day[data-date="${date}"]`).click();}
async function change(page,c,action,date,extra={}){
  const data=await (await page.request.get(`/dispatcher/couriers/${c.id}/schedule/data/?month=${date.slice(0,7)}`)).json();
  return page.request.post(`/dispatcher/couriers/${c.id}/schedule/change/`,{headers:{'X-CSRFToken':await csrf(page)},data:{action,dates:[date],revision:data.rows[0].revision,request_id:require('crypto').randomUUID(),...extra}});
}
async function noOverflow(page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBeTruthy();}

test('personal calendar: single, range, cancellation, month navigation without reload',async({dispatcherPage:page},testInfo)=>{
  const c=await createCourier(page);await openSchedule(page,c);
  await page.evaluate(()=>window.scheduleSentinel='alive');
  await expect(page.locator('.schedule-day')).toHaveCount(29);
  await day(page,'2032-02-20');
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/off/);
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('[data-action=cancel]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/unplanned/);
  await page.locator('#schedule-range [name=from]').fill('2032-02-20');
  await page.locator('#schedule-range [name=to]').fill('2032-02-22');
  await page.getByRole('button',{name:'Выбрать диапазон'}).click();
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 3');
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator('.schedule-day.off')).toHaveCount(3);
  await noOverflow(page);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0);});
  await page.screenshot({path:testInfo.outputPath('personal-calendar.png'),fullPage:true});
  await page.getByRole('button',{name:'Следующий месяц'}).click();
  await expect(page.locator('#schedule-month')).toHaveValue('2032-03');
  await expect(page.locator('.schedule-day')).toHaveCount(31);
  await page.getByRole('button',{name:'Предыдущий месяц'}).click();
  await expect(page.locator('.schedule-day.off')).toHaveCount(3);
  expect(await page.evaluate(()=>window.scheduleSentinel)).toBe('alive');
  const font=await page.locator('#schedule-comment').evaluate(el=>parseFloat(getComputedStyle(el).fontSize));expect(font).toBeGreaterThanOrEqual(16);
});

test('failed save retains date and actual state; team grid stays inside viewport',async({dispatcherPage:page},testInfo)=>{
  const c=await createCourier(page);await openSchedule(page,c);
  await day(page,'2032-02-21');
  await page.route('**/schedule/change/',route=>route.abort());
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveClass(/error/);
  await expect(page.locator('[data-date="2032-02-21"]')).toHaveClass(/unplanned/);
  await expect(page.locator('[data-date="2032-02-21"]')).toHaveAttribute('aria-pressed','true');
  await page.unroute('**/schedule/change/');
  await page.goto('/dispatcher/couriers/schedule/?month=2032-02');
  await expect(page.locator('#schedule-feedback')).toHaveText('График обновлён');
  await page.locator(`.schedule-day[data-courier="${c.id}"][data-date="2032-02-21"]`).click();
  await expect(page.locator('#schedule-details')).toContainText('Команда на эту дату');
  await noOverflow(page);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0);});
  await page.screenshot({path:testInfo.outputPath('team-calendar.png'),fullPage:true});
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator(`.schedule-day[data-courier="${c.id}"][data-date="2032-02-21"]`)).toHaveClass(/off/);
});

test('conflict warning resolves when replacement assigned; blocked assignment rolls back select',async({dispatcherPage:page})=>{
  const c=await createCourier(page), replacement=await createCourier(page);
  const tomorrow=await page.evaluate(()=>{const d=new Date(new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Moscow'})+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+1);return d.toISOString().slice(0,10);});
  const res=await page.request.post('/dispatcher/routes/new/',{form:{csrfmiddlewaretoken:await csrf(page),name:'Schedule '+c.username,default_courier:c.id}});
  const routeUrl=new URL(res.url()).pathname;await page.goto(routeUrl+'?date='+tomorrow);
  const template=await page.locator('#generate-route-form [name=template_id]').inputValue();
  const routeId=routeUrl.match(/routes\/(\d+)/)[1];
  await page.request.post(`/dispatcher/routes/${routeId}/generate/`,{form:{csrfmiddlewaretoken:await csrf(page),template_id:template,run_date:tomorrow,courier_id:c.id}});
  await openSchedule(page,c,tomorrow.slice(0,7));await day(page,tomorrow);
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('[data-action=off]').click();await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator(`.schedule-day[data-date="${tomorrow}"]`)).toHaveClass(/conflict/);
  const runUrl=await page.locator('#schedule-details a[href*="/runs/"]').getAttribute('href');
  await page.goto('/dispatcher/');await expect(page.locator('#schedule-warnings')).toContainText(c.username);
  await page.goto(runUrl);const select=page.locator('.run-reassign-select');
  await select.selectOption(String(replacement.id));await expect(page.locator('.route-now-courier')).toContainText(replacement.username);
  await expect(page.locator(`.run-reassign-select option[value="${c.id}"]`)).toContainText('Выходной');
  await page.goto('/dispatcher/');await expect(page.locator('#schedule-warnings')).not.toContainText(c.username);
  await page.goto(runUrl);await page.locator('.run-reassign-select').selectOption(String(c.id));
  await expect(page.locator('#schedule-assignment-conflict')).toBeVisible();
  await expect(page.locator('.run-reassign-select')).toHaveValue(String(replacement.id));
  await page.getByRole('button',{name:'Отменить',exact:true}).click();
});

test('stale tab cannot overwrite newer schedule; courier cannot open dispatcher schedule',async({dispatcherPage:page})=>{
  const c=await createCourier(page);await openSchedule(page,c);
  await day(page,'2032-02-20');
  expect((await change(page,c,'off','2032-02-22')).ok()).toBeTruthy();
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toContainText('изменён другим диспетчером');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/unplanned/);
  await page.request.post('/logout/',{form:{csrfmiddlewaretoken:await csrf(page)}});
  await page.goto('/login/');await page.locator('[name=username]').fill(c.username);await page.locator('[name=password]').fill('local-ui-only-password');
  await page.locator('button[type=submit]').click();await expect(page).toHaveURL(/\/courier\//);
  const response=await page.goto(c.href);expect(response.status()).toBe(403);
});
