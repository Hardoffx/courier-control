(() => {
  const root = document.getElementById('courier-schedule');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const symbols = {worked:'✓',off:'−',shift:'↗',unplanned:'·',outside:'—',conflict:'!'};
  let data, selectedDate = new URL(location.href).searchParams.get('date'), selectedCourier = Number(root.dataset.courier) || null;
  let selected = new Set(selectedDate ? [selectedDate] : []), busy = false, loading = false, controller;
  const month = $('schedule-month');
  month.value = new URL(location.href).searchParams.get('month') || new Date().toLocaleDateString('sv-SE', {timeZone:'Europe/Moscow'}).slice(0,7);
  function node(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if(cls) e.className = cls; return e; }
  function feedback(text, error=false) { $('schedule-feedback').textContent=text; $('schedule-feedback').classList.toggle('error',error); }
  function row() { return data?.rows.find(r => r.id === selectedCourier); }
  function selection() { $('schedule-selection').textContent = `Выбрано дат: ${selected.size}`; }
  function dayButton(r, d, team=false) {
    const e=node('button', undefined, `schedule-day ${d.status}${d.today?' today':''}`);
    e.type='button'; e.dataset.date=d.date; e.dataset.courier=r.id;
    e.setAttribute('aria-label', `${r.name}, ${d.date}: ${d.label}${d.today?', сегодня':''}`);
    e.setAttribute('aria-pressed', String(r.id===selectedCourier && selected.has(d.date)));
    const label=node('small', team?symbols[d.status]:`${symbols[d.status]} ${d.label}`);label.dataset.symbol=symbols[d.status];
    e.append(node('b',d.number),label);
    return e;
  }
  function render() {
    const focused=document.activeElement?.closest('.schedule-day');
    const focusDate=focused?.dataset.date,focusCourier=focused?.dataset.courier;
    const oldScroll=$('schedule-grid').querySelector('.schedule-team-scroll');
    const scrollPosition=oldScroll?{left:oldScroll.scrollLeft,top:oldScroll.scrollTop}:null;
    const grid=$('schedule-grid'); grid.replaceChildren();
    if(root.dataset.courier) {
      const r=data.rows[0];
      if(!r) return;
      const summary=$('schedule-summary'); summary.replaceChildren();
      [['worked','Отработано'],['off','Прошедшие выходные'],['shifts','Смены: сегодня и план'],['planned_off','Выходные: сегодня и план']].forEach(([key,label])=>{
        const e=node('article'); e.append(node('strong',r.counts[key]),node('span',label)); summary.append(e);
      });
      const cal=node('div',undefined,'schedule-calendar');
      ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].forEach(s=>cal.append(node('div',s,'schedule-weekday')));
      for(let i=0;i<data.weekday;i++) cal.append(node('div'));
      r.days.forEach(d=>cal.append(dayButton(r,d))); grid.append(cal);
      const period=$('schedule-period'); period.elements.start.value=r.start; period.elements.end.value=r.end;
      const audit=$('schedule-audit'); audit.replaceChildren();
      const labels={off:'Выходные отмечены',cancel:'Выходные отменены',correct:'История исправлена',period:'Период учёта изменён',assignment:'Назначение',assignment_removed:'Назначение изменено',legacy_snapshot:'Перенос сохранившихся данных'};
      (data.audit||[]).forEach(a=>audit.append(node('p',`${new Date(a.at).toLocaleString('ru-RU')} · ${a.actor} · ${labels[a.action]||a.action} · ${a.details.request?.comment||a.details.date||''}`,'schedule-audit-item')));
    } else {
      grid.append(node('p','Нажми на дату: увидишь доступность и назначения команды. Таблица прокручивается внутри карточки.','muted'));
      const scroll=node('div',undefined,'schedule-team-scroll'); scroll.tabIndex=0; scroll.setAttribute('aria-label','Календарь команды с горизонтальной прокруткой');
      const table=node('table',undefined,'schedule-team'), head=node('thead'), tr=node('tr'); tr.append(node('th','Курьер'));
      (data.rows[0]?.days||[]).forEach(d=>tr.append(node('th',d.number))); head.append(tr); table.append(head);
      const body=node('tbody');
      data.rows.forEach(r=>{ const line=node('tr'), name=node('th'), a=node('a',r.name); a.href=`${r.url}?month=${data.month}`; name.scope='row'; name.append(a); line.append(name);
        r.days.forEach(d=>{ const td=node('td');td.append(dayButton(r,d,true));line.append(td); });body.append(line); });
      table.append(body);scroll.append(table);grid.append(scroll);
      if(!data.rows.length)grid.append(node('p','Курьеров для этого фильтра нет.'));
    }
    selection(); renderDetails();
    if(focusDate)grid.querySelector(`[data-courier="${focusCourier}"][data-date="${focusDate}"]`)?.focus({preventScroll:true});
    const scroll=grid.querySelector('.schedule-team-scroll');
    if(scroll&&scrollPosition){scroll.scrollLeft=scrollPosition.left;scroll.scrollTop=scrollPosition.top;}
  }
  function updateControls(){
    root.querySelectorAll('button,input,textarea,select').forEach(e=>e.disabled=busy||loading);
    const day=row()?.days.find(d=>d.date===selectedDate);
    root.querySelectorAll('[data-action]').forEach(e=>e.disabled=busy||loading||!!day?.past);
  }
  function renderDetails() {
    const r=row(), d=r?.days.find(d=>d.date===selectedDate), details=$('schedule-details');
    details.hidden=!d; $('schedule-edit').hidden=!d;
    if(!d){updateControls();return;}
    details.replaceChildren(node('h2',`${r.name} · ${new Date(d.date+'T12:00:00').toLocaleDateString('ru-RU')}`),node('p',`${d.label}${d.today?' · Сегодня':''} · Рейсов: ${d.run_count}`));
    if(d.loose_deliveries)details.append(node('p',`Отдельных доставок без маршрута: ${d.loose_deliveries}. Они не считаются сменой маршрута.`));
    if(d.day_off)details.append(node('p',`Запланирован выходной${d.comment?': '+d.comment:''}`));
    if(d.last_activity)details.append(node('p',`Последнее выполнение: ${new Date(d.last_activity).toLocaleString('ru-RU')}`));
    const links=node('div',undefined,'schedule-route-links');d.routes.forEach(route=>{const e=node(route.url?'a':'span',route.name);if(route.url)e.href=route.url;links.append(e);});details.append(links);
    if(!root.dataset.courier){
      const a=node('a','Открыть личный график','btn alt');a.href=`${r.url}?month=${data.month}&date=${d.date}`;details.append(a);
      const list=node('ul');data.rows.forEach(c=>{const day=c.days.find(x=>x.date===d.date);list.append(node('li',`${c.name}: ${day.label}${day.run_count?' · рейсов: '+day.run_count:''}`));});details.append(node('h3','Команда на эту дату'),list);
    }
    $('schedule-correction').hidden=!d.past;
    updateControls();
    const range=$('schedule-range'), dates=[...selected].sort();range.elements.from.value=dates[0]||selectedDate;range.elements.to.value=dates[dates.length-1]||selectedDate;
  }
  async function load(history=false) {
    controller?.abort(); const current=new AbortController();controller=current;
    loading=true;updateControls();root.setAttribute('aria-busy','true');
    $('schedule-grid').classList.add('schedule-loading');
    try {
      const url=new URL(root.dataset.api,location.origin);url.searchParams.set('month',month.value);if($('schedule-active')?.checked)url.searchParams.set('active','1');
      const response=await fetch(url,{signal:current.signal});const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'Не удалось загрузить график');
      data=result;
      if(selectedDate&&!selectedDate.startsWith(data.month)){selectedDate=null;selected.clear();}
      if(!selectedDate && root.dataset.courier){selectedDate=data.rows[0]?.days.find(d=>d.today)?.date||data.rows[0]?.days[0]?.date;selected=new Set(selectedDate?[selectedDate]:[]);}
      render(); feedback('График обновлён');
      if(history){const u=new URL(location.href);u.searchParams.set('month',data.month);if(selectedDate)u.searchParams.set('date',selectedDate);else u.searchParams.delete('date');window.history.pushState({},'',u);}
      return true;
    }catch(err){if(err.name!=='AbortError'){if(data)month.value=data.month;feedback(err.message,true);}return false;}
    finally{if(controller===current){loading=false;updateControls();root.setAttribute('aria-busy','false');$('schedule-grid').classList.remove('schedule-loading');}}
  }
  async function save(action, extra={}) {
    if(busy||loading||!row())return;
    busy=true;updateControls();feedback('Сохранение…');
    const request = {action,dates:[...selected].sort(),comment:$('schedule-comment').value,revision:row().revision,request_id:crypto.randomUUID(),...extra};
    try {
      const send=()=>fetch(`/dispatcher/couriers/${selectedCourier}/schedule/change/`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':root.querySelector('[name=csrfmiddlewaretoken]').value},body:JSON.stringify(request)});
      let response=await send(), result=await response.json();
      if(response.status===409&&action==='off'&&result.schedule_url&&window.confirm(result.error+' Сохранить конфликт? Назначения останутся до ручной замены.')){
        request.allow_conflict=true;request.request_id=crypto.randomUUID();response=await send();result=await response.json();
      }
      if(!response.ok||!result.ok)throw new Error(result.error||'Не удалось сохранить');
      if(await load())feedback('Сохранено');else feedback('Изменение сохранено, но обновить график не удалось. Обнови страницу.',true);
    }catch(err){feedback(err.message,true);}
    finally{busy=false;renderDetails();}
  }
  $('schedule-grid').addEventListener('click',e=>{
    const button=e.target.closest('[data-date]');if(!button||busy||loading)return;
    const newCourier=Number(button.dataset.courier);
    if(newCourier!==selectedCourier){selected.clear();$('schedule-comment').value='';}
    selectedCourier=newCourier;selectedDate=button.dataset.date;
    if(!$('schedule-multi').checked)selected.clear();
    if($('schedule-multi').checked&&selected.has(selectedDate))selected.delete(selectedDate);else selected.add(selectedDate);
    render();
  });
  root.querySelectorAll('[data-month-step]').forEach(e=>e.addEventListener('click',()=>{
    const [y,m]=month.value.split('-').map(Number);const date=new Date(y,m-1+Number(e.dataset.monthStep),1,12);
    if(date.getFullYear()<1901||date.getFullYear()>2198)return;
    month.value=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}`;void load(true);
  }));
  month.addEventListener('change',()=>{if(month.value)void load(true);});$('schedule-active')?.addEventListener('change',()=>void load());
  root.querySelectorAll('[data-action]').forEach(e=>e.addEventListener('click',()=>void save(e.dataset.action)));
  root.querySelectorAll('[data-correct]').forEach(e=>e.addEventListener('click',()=>{
    if(window.confirm('Исправить учёт выбранных прошедших дат? Причина будет сохранена.'))void save('correct',{worked:e.dataset.correct==='true'});
  }));
  $('schedule-range').addEventListener('submit',e=>{
    e.preventDefault();if(busy)return;
    const from=e.target.elements.from.value,to=e.target.elements.to.value;
    if(!from||!to||from>to){feedback('Проверь начало и конец диапазона',true);return;}
    const dates=[];let d=new Date(from+'T12:00:00Z');const end=new Date(to+'T12:00:00Z');
    while(d<=end&&dates.length<=62){dates.push(d.toISOString().slice(0,10));d.setUTCDate(d.getUTCDate()+1);}
    if(dates.length>62){feedback('Можно выбрать не более 62 дат',true);return;}
    selected=new Set(dates);$('schedule-multi').checked=true;render();feedback('Диапазон выбран');
  });
  $('schedule-period')?.addEventListener('submit',e=>{e.preventDefault();void save('period',{start:e.target.elements.start.value,end:e.target.elements.end.value});});
  window.addEventListener('popstate',()=>{const u=new URL(location.href);month.value=u.searchParams.get('month')||month.value;selectedDate=u.searchParams.get('date');selected=new Set(selectedDate?[selectedDate]:[]);void load();});
  void load();
})();
