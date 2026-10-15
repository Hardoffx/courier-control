const {test,expect}=require('./fixtures');

async function openPersonal(page){
  await page.goto('/dispatcher/couriers/');
  const url=await page.locator('.courier-desktop a[href$="/schedule/"]').first().getAttribute('href');
  await page.goto(url+'?month=2032-02');
  await expect(page.locator('#schedule-feedback')).toHaveText('График обновлён');
}

test('calendar keeps keyboard focus after day selection',async({dispatcherPage:page})=>{
  await openPersonal(page);
  const day=page.locator('[data-date="2032-02-20"]');
  await day.focus();await day.press('Enter');
  await expect(day).toBeFocused();
  await day.press('Tab');
  await expect(page.locator('[data-date="2032-02-21"]')).toBeFocused();
});

test('month loading blocks stale edits and failure restores displayed month',async({dispatcherPage:page})=>{
  await openPersonal(page);
  await page.route('**/schedule/data/?month=2032-03',async route=>{
    await new Promise(resolve=>setTimeout(resolve,500));await route.abort();
  });
  await page.getByRole('button',{name:'Следующий месяц'}).click();
  await expect(page.locator('[data-action=off]')).toBeDisabled();
  await expect(page.locator('#schedule-feedback')).toHaveClass(/error/);
  await expect(page.locator('#schedule-month')).toHaveValue('2032-02');
  await expect(page.locator('[data-date="2032-02-20"]')).toBeVisible();
  await expect(page.locator('[data-action=off]')).toBeEnabled();
});

test('team day selection keeps horizontal scroll and focused cell',async({dispatcherPage:page})=>{
  await page.goto('/dispatcher/couriers/schedule/?month=2032-02');
  await expect(page.locator('#schedule-feedback')).toHaveText('График обновлён');
  const day=page.locator('[data-date="2032-02-28"]').first();
  await day.scrollIntoViewIfNeeded();
  const before=await page.locator('.schedule-team-scroll').evaluate(el=>el.scrollLeft);
  await day.focus();
  await day.click();
  expect(await page.locator('.schedule-team-scroll').evaluate(el=>el.scrollLeft)).toBe(before);
  await expect(day).toBeFocused();
});

test('team header stays above employee names while scrolling a long list',async({dispatcherPage:page})=>{
  await page.route('**/couriers/schedule/data/**',async route=>{
    const response=await route.fetch(),data=await response.json(),employee=data.rows[0];
    data.rows=Array.from({length:40},(_,i)=>({...employee,id:100000+i,name:'Курьер '+i}));
    await route.fulfill({response,json:data});
  });
  await page.goto('/dispatcher/couriers/schedule/?month=2032-02');
  await expect(page.locator('#schedule-feedback')).toHaveText('График обновлён');
  await page.locator('.schedule-team-scroll').scrollIntoViewIfNeeded();
  await page.locator('.schedule-team-scroll').evaluate(el=>{el.scrollTop=80;el.scrollLeft=200;});
  await expect.poll(()=>page.locator('.schedule-team-scroll').evaluate(el=>{
    const r=el.getBoundingClientRect();return document.elementFromPoint(r.left+30,r.top+15)?.textContent;
  })).toBe('Курьер');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1)).toBeTruthy();
});
