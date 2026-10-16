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
  await expect(page.locator('#courier-schedule')).toHaveAttribute('data-loaded','true');
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
  await page.screenshot({path:testInfo.outputPath('schedule-overview.png'),fullPage:true});
  await day(page,'2032-02-20');
  await page.locator('[data-begin=plan]').click();
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/off/);
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('[data-action=cancel]').click();
  await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/unplanned/);
  await page.locator('[data-mode=range]').click();
  await day(page,'2032-02-20');
  await day(page,'2032-02-22');
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
  await page.locator('[data-begin=plan]').click();
  await page.route('**/schedule/change/',route=>route.abort());
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toHaveClass(/error/);
  await expect(page.locator('[data-date="2032-02-21"]')).toHaveClass(/unplanned/);
  await expect(page.locator('[data-date="2032-02-21"]')).toHaveAttribute('aria-pressed','true');
  await page.unroute('**/schedule/change/');
  await page.goto('/dispatcher/couriers/schedule/?month=2032-02');
  await expect(page.locator('#courier-schedule')).toHaveAttribute('data-loaded','true');
  await page.locator(`.schedule-day[data-courier="${c.id}"][data-date="2032-02-21"]`).click();
  await expect(page.locator('#schedule-details')).toContainText('Команда на эту дату');
  await noOverflow(page);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0);});
  await page.screenshot({path:testInfo.outputPath('team-calendar.png'),fullPage:true});
  await page.locator('[data-begin=plan]').click();
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
  const runUrl=await page.locator('#schedule-details a[href*="/runs/"]').getAttribute('href');
  await page.locator('[data-begin=plan]').click();
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('[data-action=off]').click();await expect(page.locator('#schedule-feedback')).toHaveText('Сохранено');
  await expect(page.locator(`.schedule-day[data-date="${tomorrow}"]`)).toHaveClass(/conflict/);
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
  await page.locator('[data-begin=plan]').click();
  expect((await change(page,c,'off','2032-02-22')).ok()).toBeTruthy();
  await page.locator('[data-action=off]').click();
  await expect(page.locator('#schedule-feedback')).toContainText('изменён другим диспетчером');
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/unplanned/);
  await page.getByRole('button',{name:'Обновить график',exact:true}).click();
  await expect(page.locator('[data-action=off]')).toBeEnabled();
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('[data-action=off]').click();
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/off/);
  await page.request.post('/logout/',{form:{csrfmiddlewaretoken:await csrf(page)}});
  await page.goto('/login/');
  // This scenario checks authorization; native WebKit focus is covered by the login smoke tests.
  const login=await page.request.post('/login/',{form:{csrfmiddlewaretoken:await csrf(page),username:c.username,password:'local-ui-only-password'}});
  expect(login.ok()).toBeTruthy();expect(new URL(login.url()).pathname).toMatch(/\/courier\//);
  const response=await page.goto(c.href);expect(response.status()).toBe(403);
});

test('multiple selection, deselection and clear never leak dates across modes or months',async({dispatcherPage:page})=>{
  const c=await createCourier(page);await openSchedule(page,c);
  await day(page,'2032-02-20');
  await expect(page.locator('#schedule-edit')).toBeHidden();
  await page.locator('[data-begin=plan]').click();
  await page.locator('[data-mode=multiple]').click();
  for(const date of ['2032-02-20','2032-02-22','2032-02-24','2032-02-22'])await day(page,date);
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 2');
  await page.locator('[data-action=off]').click();
  await expect(page.locator('.schedule-day.off')).toHaveCount(2);
  await expect(page.locator('[data-kpi=planned_off] strong')).toHaveText('2');
  await expect(page.locator('[data-kpi=off] strong')).toHaveText('0');
  await expect(page.locator('[data-kpi=worked] strong')).toHaveText('0');
  await page.locator('[data-mode=range]').click();
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 0');
  await day(page,'2032-02-25');await day(page,'2032-02-23');
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 3');
  await day(page,'2032-02-24');
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 2');
  await expect(page.locator('[data-mode=multiple]')).toHaveAttribute('aria-pressed','true');
  await page.locator('#schedule-clear').click();
  await expect(page.locator('[data-action=off]')).toBeDisabled();
  await page.getByRole('button',{name:'Следующий месяц'}).click();
  await expect(page.locator('.schedule-day')).toHaveCount(31);
  await expect(page.locator('#schedule-edit')).toBeHidden();
  await expect(page.locator('[data-kpi=planned_off] strong')).toHaveText('0');
  await day(page,'2032-03-05');await page.locator('[data-begin=plan]').click();
  await expect(page.locator('#schedule-selection')).toHaveText('Выбрано дат: 1');
  await page.locator('#schedule-stop').click();await expect(page.locator('[data-begin=plan]')).toBeFocused();
  await noOverflow(page);
});

test('history correction requires reason, supports past dates and records audited counts without reload',async({dispatcherPage:page})=>{
  const c=await createCourier(page);await openSchedule(page,c,'2020-02');
  await page.evaluate(()=>window.scheduleSentinel='alive');
  await expect(page.locator('.schedule-kpi-group').first()).toContainText('Прошло');
  await expect(page.locator('.schedule-kpi-group').last()).toContainText('Предстоит');
  await expect(page.locator('#schedule-summary')).not.toContainText(/Смены|В плане/);
  await day(page,'2020-02-12');
  await expect(page.locator('#schedule-details')).toContainText('Нет подтверждённых данных');
  await expect(page.locator('#schedule-details')).not.toContainText(c.username);
  await page.locator('[data-begin=history]').click();
  await page.locator('[data-mode=multiple]').click();
  await day(page,'2020-02-12');await day(page,'2020-02-13');
  await page.getByRole('radio',{name:'Работал',exact:true}).check();
  let requests=0;page.on('request',r=>{if(r.url().endsWith('/schedule/change/'))requests++;});
  await page.getByRole('button',{name:'Сохранить исправление',exact:true}).click();
  expect(requests).toBe(0);
  await expect(page.locator('#schedule-reason')).toBeFocused();
  await page.locator('#schedule-reason').fill('Подтверждено по журналу смен');
  await page.getByRole('button',{name:'Сохранить исправление',exact:true}).click();
  await expect(page.locator('.schedule-day.worked')).toHaveCount(2);
  await expect(page.locator('[data-kpi=worked] strong')).toHaveText('2');
  await expect(page.locator('[data-kpi=shifts] strong')).toHaveText('0');
  await expect(page.locator('[data-date="2020-02-12"]')).toHaveAttribute('aria-pressed','true');
  await page.getByRole('radio',{name:'Выходной',exact:true}).check();
  await page.locator('#schedule-reason').fill('Уточнение: подтверждены выходные');
  await page.getByRole('button',{name:'Сохранить исправление',exact:true}).click();
  await expect(page.locator('.schedule-day.off')).toHaveCount(2);
  await expect(page.locator('[data-kpi=worked] strong')).toHaveText('0');
  await expect(page.locator('[data-kpi=off] strong')).toHaveText('2');
  await page.locator('#schedule-stop').click();
  await page.getByText('История и настройки',{exact:true}).click();
  await page.getByText('Последние изменения',{exact:true}).click();
  await expect(page.locator('#schedule-audit')).toContainText('Подтверждено по журналу смен');
  await expect(page.locator('#schedule-audit')).toContainText('Уточнение: подтверждены выходные');
  await expect(page.locator('#schedule-audit')).toContainText('назначение действовало');
  await expect(page.locator('#schedule-feedback')).toBeHidden({timeout:5000});
  expect(await page.evaluate(()=>window.scheduleSentinel)).toBe('alive');
  await noOverflow(page);
});

test('month picker crosses year boundary and team employee filter clears editing',async({dispatcherPage:page})=>{
  const c=await createCourier(page);await openSchedule(page,c,'2031-12');
  await page.getByRole('button',{name:'Следующий месяц'}).click();
  await expect(page.locator('#schedule-month-title')).toHaveText('Январь 2032');
  await expect(page.locator('.schedule-day')).toHaveCount(31);
  await page.locator('#schedule-month-title').click();
  await page.locator('#schedule-month').fill('2032-02');
  await expect(page.locator('.schedule-day')).toHaveCount(29);
  await expect(page.locator('.schedule-month-picker')).not.toHaveAttribute('open','');
  await page.goto('/dispatcher/couriers/schedule/?month=2032-02');
  await expect(page.locator('#courier-schedule')).toHaveAttribute('data-loaded','true');
  await page.locator('#schedule-employee').selectOption(String(c.id));
  await expect(page.locator('.schedule-team tbody tr')).toHaveCount(1);
  await day(page,'2032-02-21');await page.locator('[data-begin=plan]').click();
  await page.locator('#schedule-employee').selectOption('');
  await expect(page.locator('#schedule-edit')).toBeHidden();
  await expect(page.locator('#schedule-details')).toBeHidden();
  await expect(page.locator('.schedule-team tbody tr a')).toContainText([c.username]);
  await noOverflow(page);
});

test('lost save reply retries the identical UUID without duplicate audit or stale state',async({dispatcherPage:page})=>{
  const c=await createCourier(page);await openSchedule(page,c);
  await day(page,'2032-02-20');await page.locator('[data-begin=plan]').click();
  const bodies=[];
  await page.route('**/schedule/change/',async route=>{
    bodies.push(route.request().postData());
    if(bodies.length===1){
      const response=await route.fetch();expect(response.ok()).toBeTruthy();
      await new Promise(resolve=>setTimeout(resolve,250));await route.abort();
    }else await route.continue();
  });
  await page.locator('[data-action=off]').click();
  await expect(page.locator('[data-action=off]')).toBeDisabled();
  await expect(page.locator('#schedule-feedback')).toHaveClass(/error/);
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/unplanned/);
  await page.locator('[data-action=off]').click();
  await expect(page.locator('[data-date="2032-02-20"]')).toHaveClass(/off/);
  expect(bodies).toHaveLength(2);expect(bodies[0]).toBe(bodies[1]);
  const result=await(await page.request.get(`/dispatcher/couriers/${c.id}/schedule/data/?month=2032-02`)).json();
  expect(result.audit.filter(a=>a.action==='off')).toHaveLength(1);
  await page.emulateMedia({reducedMotion:'reduce'});
  expect(await page.locator('.schedule-day').first().evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
});
