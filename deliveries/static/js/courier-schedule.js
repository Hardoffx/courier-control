(() => {
  const root = document.getElementById('courier-schedule');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const personal = !!root.dataset.courier;
  const symbols = {worked:'✓', off:'−', shift:'↗', unplanned:'·', outside:'', conflict:'!'};
  const month = $('schedule-month');
  const initial = new URL(location.href);
  month.value = initial.searchParams.get('month') || new Date().toLocaleDateString('sv-SE', {timeZone:'Europe/Moscow'}).slice(0,7);
  let data, selectedDate = initial.searchParams.get('date'), selectedCourier = Number(root.dataset.courier) || null;
  let selected = new Set(), intent = null, mode = 'single', anchor = null, rangeComplete = false;
  let busy = false, loading = false, controller, noticeTimer, stale = false, pendingRequest;
  let teamHintDismissed = false;

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
    e.setAttribute('aria-label', `${team?r.name+', ':''}${dateText(d.date, {day:'numeric', month:'long', year:'numeric'})}${d.status === 'outside'?'':': '+d.label}${d.today?', сегодня':''}`);
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
  function humanAuditDate(value) {
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return dateText(value, {day:'numeric', month:'long', year:'numeric'});
    }
    return String(value || '');
  }
  function auditCard(a) {
    const detail = a.details || {}, request = detail.request || {};
    const labels = {off:'Выходной отмечен', cancel:'Выходной отменён',
      correct:'Статус исправлен', period:'Период учёта', assignment:'Назначение',
      assignment_removed:'Назначение изменено', legacy_snapshot:'Перенос данных'};
    const kind = a.action === 'assignment_removed' ? 'assignment' : a.action === 'legacy_snapshot' ? 'system' : a.action;
    const card = node('article', undefined, 'schedule-audit-item');
    const meta = node('div', undefined, 'schedule-audit-meta');
    const time = node('time'), instant = new Date(a.at);
    time.dateTime = a.at;
    time.textContent = Number.isNaN(instant.getTime()) ? String(a.at) :
      instant.toLocaleString('ru-RU', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'});
    meta.append(time, node('span', a.actor || 'Система', 'schedule-audit-actor'));
    card.append(meta, node('span', labels[a.action] || a.action, 'schedule-audit-badge '+(kind || 'system')));
    const dates = Array.isArray(request.dates) ? request.dates : detail.date ? [detail.date] : [];
    let summary = '';
    const datesBrief = dates.length <= 2 ? dates.map(humanAuditDate).join(', ') :
      dates.slice(0,2).map(humanAuditDate).join(', ')+' и ещё '+(dates.length-2);
    if (a.action === 'correct') summary = 'Исправлен день: '+datesBrief;
    else if (a.action === 'off' || a.action === 'cancel') summary = 'Даты: '+datesBrief;
    else if (a.action === 'assignment') summary = 'Маршрут '+(detail.route || '')+(detail.date?' · '+humanAuditDate(detail.date):'');
    else if (a.action === 'assignment_removed') summary = 'Изменено назначение'+(detail.date?' · '+humanAuditDate(detail.date):'');
    else if (a.action === 'legacy_snapshot') summary = 'Сохранены исторические сведения'+(detail.date?' · '+humanAuditDate(detail.date):'');
    else if (a.action === 'period') summary = 'Границы периода учёта';
    else summary = detail.date ? humanAuditDate(detail.date) : 'Изменение графика';
    card.append(node('p', summary, 'schedule-audit-primary'));
    if (a.action === 'correct') card.append(node('p', request.worked ? 'Установлен статус: работал' : 'Установлен статус: выходной', 'schedule-audit-secondary'));
    if (a.action === 'assignment_removed' && detail.retained) card.append(node('p', 'Свидетельство за прошедший день сохранено', 'schedule-audit-secondary'));
    if (dates.length > 2) {
      const all = node('details', undefined, 'schedule-audit-more');
      all.append(node('summary', 'Все даты ('+dates.length+')'),
        node('p', dates.map(humanAuditDate).join(', '), 'schedule-audit-secondary'));
      card.append(all);
    }
    const comment = String(request.comment || '').trim();
    if (comment && comment !== '.') card.append(node('p', (a.action === 'correct'?'Причина: ':'Комментарий: ')+comment, 'schedule-audit-secondary'));
    const before = detail.before;
    if (Array.isArray(before) && before.length) {
      const previous = before.map(d => {
        const event = a.action === 'correct' ? 'назначение' : 'выходной';
        return humanAuditDate(d.date)+': '+event+' '+(d.active?'действовало':'отменено');
      }).join('; ');
      card.append(node('p', 'Было: '+previous, 'schedule-audit-secondary'));
    } else if (before && !Array.isArray(before)) {
      card.append(node('p', 'Прежний период: '+humanAuditDate(before.start)+' — '+
        (before.end && before.end !== 'None'?humanAuditDate(before.end):'без окончания'), 'schedule-audit-secondary'));
    }
    if (Array.isArray(detail.previous_days_off) && detail.previous_days_off.length) {
      const earlier = detail.previous_days_off.map(d => humanAuditDate(d.date)+' — '+(d.active?'отмечен':'отменён')).join('; ');
      card.append(node('p', 'Прежние выходные: '+earlier, 'schedule-audit-secondary'));
    }
    return card;
  }
  function renderAudit() {
    const audit = $('schedule-audit');
    audit.replaceChildren();
    const entries = data.audit || [];
    if (!entries.length) {
      audit.append(node('p', 'Изменений пока нет.', 'muted'));
      return;
    }
    entries.filter(a => a.action !== 'legacy_snapshot').forEach(a => audit.append(auditCard(a)));
    const technical = entries.filter(a => a.action === 'legacy_snapshot');
    if (technical.length) {
      const group = node('details', undefined, 'schedule-audit-system');
      group.append(node('summary', 'Системные записи ('+technical.length+')'));
      technical.forEach(a => group.append(auditCard(a)));
      audit.append(group);
    }
  }
  function renderTeam(grid) {
    const filter = $('schedule-employee'), value = filter.value;
    const shortCounts = new Map();
    data.rows.forEach(r => { const label = r.short_name || r.name; shortCounts.set(label, (shortCounts.get(label) || 0) + 1); });
    filter.replaceChildren(new Option('Все сотрудники', ''));
    data.rows.forEach(r => filter.add(new Option(r.name, String(r.id))));
    filter.value = data.rows.some(r => String(r.id) === value) ? value : '';
    const scroll = node('div', undefined, 'schedule-team-scroll');
    scroll.tabIndex = 0; scroll.setAttribute('aria-label', 'Календарь команды с горизонтальной прокруткой');
    const table = node('table', undefined, 'schedule-team'), head = node('thead'), tr = node('tr');
    const corner = node('th', 'Курьер'); corner.scope = 'col'; tr.append(corner);
    (data.rows[0]?.days || []).forEach(d => {
      const th = node('th'), dateHead = node('span', undefined, 'schedule-team-date');
      const weekday = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'][new Date(d.date+'T12:00:00Z').getUTCDay()];
      dateHead.append(node('b', d.number), node('small', weekday));
      th.scope = 'col'; th.setAttribute('aria-label', dateText(d.date, {day:'numeric', month:'long', year:'numeric', weekday:'long'}));
      th.append(dateHead); tr.append(th);
    });
    head.append(tr); table.append(head);
    const body = node('tbody');
    data.rows.filter(r => !filter.value || String(r.id) === filter.value).forEach(r => {
      const line = node('tr'), name = node('th'), a = node('a');
      const mobileName = r.short_name || r.name, duplicate = shortCounts.get(mobileName) > 1;
      a.href = `${r.url}?month=${data.month}`; a.title = r.name;
      a.setAttribute('aria-label', r.name + (duplicate ? ', сотрудник №'+r.id : ''));
      const shortLabel = node('span', undefined, 'schedule-name-mobile');
      const shortParts = mobileName.match(/^(.+)\s([^\s])\.$/u);
      shortLabel.append(node('span', shortParts ? shortParts[1] : mobileName, 'schedule-name-surname'));
      if (shortParts) shortLabel.append(node('span', ' '+shortParts[2]+'.', 'schedule-name-initial'));
      a.append(node('span', r.name, 'schedule-name-desktop'), shortLabel);
      if (duplicate) a.append(node('span', '№'+r.id, 'schedule-name-duplicate'));
      name.scope = 'row'; name.append(a); line.append(name);
      r.days.forEach(d => {const td = node('td'); td.append(dayButton(r,d,true)); line.append(td);});
      body.append(line);
    });
    table.append(body); scroll.append(table); grid.append(scroll);
    const hint = $('schedule-swipe-hint'); hint.hidden = teamHintDismissed || !data.rows.length;
    scroll.addEventListener('scroll', () => {
      if (scroll.scrollLeft > 12 && !teamHintDismissed) {
        teamHintDismissed = true; hint.hidden = true;
      }
    }, {passive:true});
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
    const statusText = d.status === 'outside' ? '' : `${d.label}${d.today?' · Сегодня':''} · `;
    details.replaceChildren(node('h2', `${personal?'':r.name+' · '}${dateText(d.date, {weekday:'long', day:'numeric', month:'long'})}`), node('p', `${statusText}Маршрутов: ${d.run_count}`));
    const note = (d.comment || '').trim();
    if (d.day_off && note && note !== '.') details.append(node('p', `Комментарий к выходному: ${note}`));
    if (d.loose_deliveries) details.append(node('p', `Отдельных доставок без маршрута: ${d.loose_deliveries}`));
    if (d.last_activity) details.append(node('p', `Последнее выполнение: ${new Date(d.last_activity).toLocaleString('ru-RU')}`));
    const links = node('div', undefined, 'schedule-route-links');
    d.routes.forEach(route => {const a = node(route.url?'a':'span', route.name); if(route.url) a.href = route.url; links.append(a);});
    details.append(links);
    const actions = node('div', undefined, 'schedule-actions'), edit = node('button', d.past?'Исправить прошедший день':d.day_off?'Изменить график':'Запланировать выходной', d.past?'btn alt schedule-history-action':'btn');
    edit.type = 'button'; edit.dataset.begin = d.past?'history':'plan'; actions.append(edit);
    if (!personal) {
      const a = node('a', 'Личный график ↗', 'btn alt'); a.href = `${r.url}?month=${data.month}&date=${d.date}`; actions.append(a);
      const team = node('details'), list = node('ul'); team.append(node('summary', 'Команда на эту дату'));
      data.rows.forEach(c => {const item = c.days.find(x => x.date === d.date); list.append(node('li', `${c.name}${item.status === 'outside'?'':': '+item.label}${item.run_count?' · маршрутов: '+item.run_count:''}`));});
      team.append(list); details.append(team);
    }
    details.append(actions);
  }
  function renderEditing() {
    $('schedule-edit').hidden = !intent; $('schedule-mode').hidden = !intent;
    $('schedule-planning').hidden = intent !== 'plan'; $('schedule-correction').hidden = intent !== 'history';
    $('schedule-mode-title').textContent = intent === 'history'?'Исправление прошедших дней':'Планирование выходных';
    root.querySelectorAll('[data-mode]').forEach(e => e.setAttribute('aria-pressed', String(e.dataset.mode === mode)));
    const hints = {single:'Нажми на одну дату. Повторное нажатие снимет выбор.', multiple:'Нажимай на нужные даты. Повторное нажатие снимет выбор.', range:anchor&&!rangeComplete?'Теперь нажми на последнюю дату диапазона.':'Нажми на первую, затем на последнюю дату диапазона.'};
    $('schedule-mode-hint').textContent = hints[mode];
    $('schedule-selection').textContent = `Выбрано дат: ${selected.size}`;
    const dates = [...selected].sort();
    $('schedule-selected-dates').textContent = dates.length ? (dates.length > 5 ? `${dateText(dates[0])} — ${dateText(dates.at(-1))} · ${dates.length} дат` : dates.map(d => dateText(d)).join(' · ')) : 'Выбери даты в календаре.';
    const statuses = [...new Set(dates.map(date => day(date)).filter(d => d && d.status !== 'outside').map(d => d.label))];
    $('schedule-current-status').textContent = statuses.length ? 'Сейчас: '+statuses.join(', ') : '';
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
  $('schedule-refresh').addEventListener('click', () => void load());
  window.addEventListener('popstate', () => {
    const url = new URL(location.href); month.value = url.searchParams.get('month') || month.value;
    selectedDate = url.searchParams.get('date'); stopEditing(); void load();
  });
  void load();
})();
