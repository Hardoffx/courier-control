(() => {
  const root = document.getElementById('courier-schedule');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const personal = !!root.dataset.courier;
  const symbols = {worked:'✓', off:'−', shift:'↗', unplanned:'·', outside:'—', conflict:'!'};
  const month = $('schedule-month');
  const initial = new URL(location.href);
  month.value = initial.searchParams.get('month') || new Date().toLocaleDateString('sv-SE', {timeZone:'Europe/Moscow'}).slice(0,7);
  let data, selectedDate = initial.searchParams.get('date'), selectedCourier = Number(root.dataset.courier) || null;
  let selected = new Set(), intent = null, mode = 'single', anchor = null, rangeComplete = false;
  let busy = false, loading = false, controller, noticeTimer, stale = false, pendingRequest;

  function node(tag, text, cls) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function row() { return data?.rows.find(r => r.id === selectedCourier); }
  function day(date = selectedDate) { return row()?.days.find(d => d.date === date); }
  function dateText(date, options = {day:'numeric', month:'short'}) {
    return new Date(date+'T12:00:00').toLocaleDateString('ru-RU', options);
  }
  function feedback(message = '', error = false) {
    clearTimeout(noticeTimer);
    $('schedule-feedback').textContent = message;
    $('schedule-feedback').classList.toggle('error', error);
    $('schedule-notice').hidden = !message;
    $('schedule-refresh').hidden = !error;
    if (message && !error) noticeTimer = setTimeout(() => feedback(), 3000);
  }
  function clearSelection() {
    selected.clear(); anchor = null; rangeComplete = false; pendingRequest = null;
  }
  function stopEditing() {
    intent = null; mode = 'single'; clearSelection();
    $('schedule-comment').value = '';
    $('schedule-correction').reset();
  }
  function updateURL(push = false) {
    const url = new URL(location.href);
    url.searchParams.set('month', data.month);
    if (selectedDate) url.searchParams.set('date', selectedDate); else url.searchParams.delete('date');
    window.history[push ? 'pushState' : 'replaceState']({}, '', url);
  }
  function dayButton(r, d, team = false) {
    const e = node('button', undefined, `schedule-day ${d.status}${d.today?' today':''}`);
    e.type = 'button'; e.dataset.date = d.date; e.dataset.courier = r.id;
    e.setAttribute('aria-label', `${team?r.name+', ':''}${dateText(d.date, {day:'numeric', month:'long', year:'numeric'})}: ${d.label}${d.today?', сегодня':''}`);
    e.setAttribute('aria-pressed', String(r.id === selectedCourier && (intent ? selected.has(d.date) : d.date === selectedDate)));
    if (d.today) e.setAttribute('aria-current', 'date');
    e.append(node('b', d.number), node('small', symbols[d.status]));
    return e;
  }
  function renderSummary(r) {
    const summary = $('schedule-summary'); summary.replaceChildren();
    const groups = [
      ['Прошло', [['worked','Отработано дней'], ['off','Выходных дней']]],
      ['Предстоит', [['shifts','Рабочих дней','Назначено'], ['planned_off','Выходных дней','Запланировано']]],
    ];
    groups.forEach(([title, metrics]) => {
      const group = node('section', undefined, 'schedule-kpi-group'), cards = node('div', undefined, 'schedule-kpi-cards');
      group.setAttribute('aria-label', title); group.append(node('h2', title));
      metrics.forEach(([key, label, hint]) => {
        const card = node('article'); card.dataset.kpi = key;
        card.append(node('strong', r.counts[key]), node('span', label));
        if (hint) card.append(node('small', hint));
        cards.append(card);
      });
      group.append(cards); summary.append(group);
    });
  }
  function renderAudit() {
    const r = row(), period = $('schedule-period'), audit = $('schedule-audit');
    period.elements.start.value = r.start; period.elements.end.value = r.end;
    audit.replaceChildren();
    const labels = {off:'Выходные отмечены', cancel:'Выходные отменены', correct:'История исправлена', period:'Период учёта изменён', assignment:'Назначение', assignment_removed:'Назначение изменено', legacy_snapshot:'Перенос сохранившихся данных'};
    (data.audit || []).forEach(a => {
      const before = a.details.before;
      const previous = Array.isArray(before) ? before.map(d => `${d.date}: ${a.action === 'correct'?'назначение':'выходной'} ${d.active?'действовало':'отменено'}`).join(', ') : before ? `${before.start} — ${before.end === 'None'?'без окончания':before.end}` : '';
      const previousOff = (a.details.previous_days_off || []).map(d => `${d.date}: выходной ${d.active?'действовал':'отменён'}`).join(', ');
      audit.append(node('p', `${new Date(a.at).toLocaleString('ru-RU')} · ${a.actor} · ${labels[a.action] || a.action}${previous?' · Было: '+previous:''}${previousOff?' · '+previousOff:''} · ${a.details.request?.comment || a.details.date || ''}`, 'schedule-audit-item'));
    });
    if (!data.audit?.length) audit.append(node('p', 'Изменений пока нет.', 'muted'));
  }
  function renderTeam(grid) {
    const filter = $('schedule-employee'), value = filter.value;
    filter.replaceChildren(new Option('Все сотрудники', ''));
    data.rows.forEach(r => filter.add(new Option(r.name, String(r.id))));
    filter.value = data.rows.some(r => String(r.id) === value) ? value : '';
    const scroll = node('div', undefined, 'schedule-team-scroll');
    scroll.tabIndex = 0; scroll.setAttribute('aria-label', 'Календарь команды с горизонтальной прокруткой');
    const table = node('table', undefined, 'schedule-team'), head = node('thead'), tr = node('tr');
    const corner = node('th', 'Курьер'); corner.scope = 'col'; tr.append(corner);
    (data.rows[0]?.days || []).forEach(d => {const th = node('th', d.number); th.scope = 'col'; tr.append(th);});
    head.append(tr); table.append(head);
    const body = node('tbody');
    data.rows.filter(r => !filter.value || String(r.id) === filter.value).forEach(r => {
      const line = node('tr'), name = node('th'), a = node('a', r.name);
      a.href = `${r.url}?month=${data.month}`; name.scope = 'row'; name.append(a); line.append(name);
      r.days.forEach(d => {const td = node('td'); td.append(dayButton(r,d,true)); line.append(td);});
      body.append(line);
    });
    table.append(body); scroll.append(table); grid.append(scroll);
    if (!data.rows.length) grid.append(node('p', 'Курьеров для этого фильтра нет.'));
  }
  function render() {
    const focused = document.activeElement?.closest('.schedule-day');
    const focusDate = focused?.dataset.date, focusCourier = focused?.dataset.courier;
    const oldScroll = $('schedule-grid').querySelector('.schedule-team-scroll');
    const position = oldScroll ? {left:oldScroll.scrollLeft, top:oldScroll.scrollTop} : null;
    const grid = $('schedule-grid'); grid.replaceChildren();
    const title = dateText(data.month+'-01', {month:'long', year:'numeric'}).replace(/ г\.$/, '');
    $('schedule-month-title').textContent = title.charAt(0).toUpperCase()+title.slice(1);
    if (personal && data.rows[0]) {
      renderSummary(data.rows[0]); renderAudit();
      const calendar = node('div', undefined, 'schedule-calendar');
      ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].forEach(s => calendar.append(node('div', s, 'schedule-weekday')));
      for (let i = 0; i < data.weekday; i++) calendar.append(node('div'));
      data.rows[0].days.forEach(d => calendar.append(dayButton(data.rows[0],d))); grid.append(calendar);
    } else renderTeam(grid);
    renderDetails(); renderEditing(); updateControls();
    if (focusDate) grid.querySelector(`[data-courier="${focusCourier}"][data-date="${focusDate}"]`)?.focus({preventScroll:true});
    const scroll = grid.querySelector('.schedule-team-scroll');
    if (scroll && position) {scroll.scrollLeft = position.left; scroll.scrollTop = position.top;}
  }
  function renderDetails() {
    const r = row(), d = day(), details = $('schedule-details');
    details.hidden = !d || !!intent;
    if (!d) return;
    details.replaceChildren(node('h2', `${personal?'':r.name+' · '}${dateText(d.date, {weekday:'long', day:'numeric', month:'long'})}`), node('p', `${d.label}${d.today?' · Сегодня':''} · Маршрутов: ${d.run_count}`));
    if (d.day_off) details.append(node('p', `Запланирован выходной${d.comment?': '+d.comment:''}`));
    if (d.loose_deliveries) details.append(node('p', `Отдельных доставок без маршрута: ${d.loose_deliveries}`));
    if (d.last_activity) details.append(node('p', `Последнее выполнение: ${new Date(d.last_activity).toLocaleString('ru-RU')}`));
    const links = node('div', undefined, 'schedule-route-links');
    d.routes.forEach(route => {const a = node(route.url?'a':'span', route.name); if(route.url) a.href = route.url; links.append(a);});
    details.append(links);
    const actions = node('div', undefined, 'schedule-actions'), edit = node('button', d.past?'Исправить историю':d.day_off?'Изменить график':'Запланировать выходной', 'btn');
    edit.type = 'button'; edit.dataset.begin = d.past?'history':'plan'; actions.append(edit);
    if (!personal) {
      const a = node('a', 'Личный график ↗', 'btn alt'); a.href = `${r.url}?month=${data.month}&date=${d.date}`; actions.append(a);
      const team = node('details'), list = node('ul'); team.append(node('summary', 'Команда на эту дату'));
      data.rows.forEach(c => {const item = c.days.find(x => x.date === d.date); list.append(node('li', `${c.name}: ${item.label}${item.run_count?' · маршрутов: '+item.run_count:''}`));});
      team.append(list); details.append(team);
    }
    details.append(actions);
  }
  function renderEditing() {
    $('schedule-edit').hidden = !intent; $('schedule-mode').hidden = !intent;
    $('schedule-planning').hidden = intent !== 'plan'; $('schedule-correction').hidden = intent !== 'history';
    $('schedule-mode-title').textContent = intent === 'history'?'Исправление истории':'Планирование выходных';
    root.querySelectorAll('[data-mode]').forEach(e => e.setAttribute('aria-pressed', String(e.dataset.mode === mode)));
    const hints = {single:'Нажми на одну дату. Повторное нажатие снимет выбор.', multiple:'Нажимай на нужные даты. Повторное нажатие снимет выбор.', range:anchor&&!rangeComplete?'Теперь нажми на последнюю дату диапазона.':'Нажми на первую, затем на последнюю дату диапазона.'};
    $('schedule-mode-hint').textContent = hints[mode];
    $('schedule-selection').textContent = `Выбрано дат: ${selected.size}`;
    const dates = [...selected].sort();
    $('schedule-selected-dates').textContent = dates.length ? (dates.length > 5 ? `${dateText(dates[0])} — ${dateText(dates.at(-1))} · ${dates.length} дат` : dates.map(d => dateText(d)).join(' · ')) : 'Выбери даты в календаре.';
    $('schedule-current-status').textContent = 'Сейчас: '+[...new Set(dates.map(d => day(d)?.label))].filter(Boolean).join(', ');
    root.querySelector('[data-action=cancel]').hidden = !dates.some(d => day(d)?.day_off);
  }
  function updateControls() {
    root.querySelectorAll('button,input,textarea,select').forEach(e => e.disabled = busy || loading);
    root.querySelectorAll('.schedule-day').forEach(e => {
      const d = data?.rows.find(r => r.id === Number(e.dataset.courier))?.days.find(d => d.date === e.dataset.date);
      e.disabled = busy || loading || !!(intent && (Number(e.dataset.courier) !== selectedCourier || d?.past !== (intent === 'history')));
    });
    root.querySelectorAll('[data-action],#schedule-correction button[type=submit]').forEach(e => e.disabled = busy || loading || stale || !selected.size);
    $('schedule-clear').disabled = busy || loading || !selected.size;
    $('schedule-loading').hidden = !loading && !busy;
    $('schedule-loading').textContent = busy?'Сохранение…':'Загрузка…';
  }
  async function load(push = false) {
    controller?.abort(); const current = new AbortController(); controller = current;
    loading = true; updateControls(); root.setAttribute('aria-busy', 'true'); $('schedule-grid').classList.add('schedule-loading');
    try {
      const url = new URL(root.dataset.api, location.origin); url.searchParams.set('month', month.value);
      if ($('schedule-active')?.checked) url.searchParams.set('active','1');
      const response = await fetch(url, {signal:current.signal}), result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Не удалось загрузить график');
      if (controller !== current) return false;
      if (data?.month !== result.month || !result.rows.some(r => r.id === selectedCourier)) stopEditing();
      data = result; stale = false;
      if (selectedDate && !selectedDate.startsWith(data.month)) selectedDate = null;
      if (personal && !selectedDate) selectedDate = data.rows[0]?.days.find(d => d.today)?.date || data.rows[0]?.days[0]?.date;
      render(); feedback(); root.dataset.loaded = 'true';
      $('schedule-month').closest('details').open = false;
      updateURL(push); return true;
    } catch (err) {
      if (err.name !== 'AbortError') {if (data) month.value = data.month; feedback(err.message, true);}
      return false;
    } finally {
      if (controller === current) {loading = false; updateControls(); root.setAttribute('aria-busy', 'false'); $('schedule-grid').classList.remove('schedule-loading');}
    }
  }
  function validateDates(action) {
    const dates = [...selected].sort();
    if (!dates.length || dates.length > 62) throw new Error('Выбери от 1 до 62 дат');
    if ((Date.parse(dates.at(-1)) - Date.parse(dates[0])) / 86400000 > 92) throw new Error('Диапазон не должен превышать 93 дня');
    if (dates.some(date => !date.startsWith(data.month) || !day(date) || day(date).past !== (action === 'correct'))) throw new Error('Прошедшие и будущие даты нужно изменять отдельно');
    return dates;
  }
  async function save(action, extra = {}) {
    if (busy || loading || stale || !row()) return;
    let request;
    try {
      request = {action, revision:row().revision, ...extra};
      if (action !== 'period') {
        request.dates = validateDates(action);
        request.comment = action === 'correct'?$('schedule-reason').value.trim():$('schedule-comment').value.trim();
        if (action === 'correct' && !request.comment) throw new Error('Укажи причину исправления');
      }
    } catch (err) {feedback(err.message, true); return;}
    const signature = JSON.stringify({courier:selectedCourier, ...request});
    request = pendingRequest?.signature === signature ? {...pendingRequest.request} : {...request, request_id:crypto.randomUUID()};
    pendingRequest = {signature, request:{...request}};
    busy = true; updateControls(); feedback();
    try {
      const send = () => fetch(`/dispatcher/couriers/${selectedCourier}/schedule/change/`, {method:'POST', headers:{'Content-Type':'application/json', 'X-CSRFToken':root.querySelector('[name=csrfmiddlewaretoken]').value}, body:JSON.stringify(request)});
      let response = await send(), result = await response.json();
      if (response.status === 409 && action === 'off' && result.schedule_url) {
        if (!window.confirm(result.error+' Сохранить конфликт? Назначения останутся до ручной замены.')) {feedback(); return;}
        request.allow_conflict = true; request.request_id = crypto.randomUUID();
        pendingRequest = {signature, request:{...request}};
        response = await send(); result = await response.json();
      }
      if (!response.ok || !result.ok) {if (response.status === 409) stale = true; throw new Error(result.error || 'Не удалось сохранить');}
      pendingRequest = null;
      if (await load()) feedback('Сохранено');
      else {stale = true; feedback('Изменение сохранено, но обновить график не удалось. Нажми «Обновить график».', true);}
    } catch (err) {feedback(err.message, true);}
    finally {busy = false; renderDetails(); renderEditing(); updateControls();}
  }
  $('schedule-details').addEventListener('click', e => {
    const button = e.target.closest('[data-begin]'); if (!button || busy || loading) return;
    stopEditing(); intent = button.dataset.begin; selected.add(selectedDate); render();
    root.querySelector('[data-mode][aria-pressed=true]').focus({preventScroll:true});
  });
  $('schedule-grid').addEventListener('click', e => {
    const button = e.target.closest('[data-date]'); if (!button || busy || loading) return;
    const courier = Number(button.dataset.courier), date = button.dataset.date;
    if (courier !== selectedCourier) stopEditing();
    selectedCourier = courier; selectedDate = date;
    if (intent) {
      if (mode === 'single') {const had = selected.has(date); clearSelection(); if (!had) selected.add(date);}
      else if (mode === 'multiple') {if (selected.has(date)) selected.delete(date); else selected.add(date);}
      else if (rangeComplete && selected.has(date)) {selected.delete(date); mode = 'multiple'; anchor = null; rangeComplete = false;}
      else if (!anchor || rangeComplete) {clearSelection(); anchor = date; selected.add(date);}
      else {
        const [first,last] = [anchor,date].sort();
        selected = new Set(row().days.filter(d => d.date >= first && d.date <= last).map(d => d.date)); rangeComplete = true;
      }
    }
    render(); updateURL();
  });
  root.querySelectorAll('[data-mode]').forEach(e => e.addEventListener('click', () => {
    if (mode === e.dataset.mode) return;
    mode = e.dataset.mode; clearSelection(); render();
  }));
  $('schedule-clear').addEventListener('click', () => {clearSelection(); render();});
  $('schedule-stop').addEventListener('click', () => {
    stopEditing(); render(); root.querySelector('[data-begin]')?.focus({preventScroll:true});
  });
  root.querySelectorAll('[data-month-step]').forEach(e => e.addEventListener('click', () => {
    const [year,m] = month.value.split('-').map(Number), next = new Date(year,m-1+Number(e.dataset.monthStep),1,12);
    if (next.getFullYear() < 1901 || next.getFullYear() > 2198) return;
    month.value = `${next.getFullYear()}-${String(next.getMonth()+1).padStart(2,'0')}`; void load(true);
  }));
  month.addEventListener('change', () => {if (month.validity.valid && month.value) void load(true);});
  $('schedule-active')?.addEventListener('change', () => {stopEditing(); void load();});
  $('schedule-employee')?.addEventListener('change', e => {
    stopEditing(); selectedCourier = Number(e.target.value) || null; selectedDate = null; render(); updateURL();
  });
  root.querySelectorAll('[data-action]').forEach(e => e.addEventListener('click', () => void save(e.dataset.action)));
  $('schedule-correction').addEventListener('submit', e => {
    e.preventDefault(); void save('correct', {worked:e.target.elements.worked.value === 'true'});
  });
  $('schedule-period')?.addEventListener('submit', e => {
    e.preventDefault(); void save('period', {start:e.target.elements.start.value, end:e.target.elements.end.value});
  });
  $('schedule-refresh').addEventListener('click', () => void load());
  window.addEventListener('popstate', () => {
    const url = new URL(location.href); month.value = url.searchParams.get('month') || month.value;
    selectedDate = url.searchParams.get('date'); stopEditing(); void load();
  });
  void load();
})();
