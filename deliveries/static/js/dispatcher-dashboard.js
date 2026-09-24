const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';

function toast(message,error=false){
  let el=document.querySelector('.ops-toast');
  if(!el){el=document.createElement('div');el.className='ops-toast';document.body.appendChild(el)}
  el.textContent=message;
  el.classList.toggle('error',error);
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

async function post(url,data){
  const body=data instanceof FormData?data:new URLSearchParams(data);
  const response=await fetch(url,{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':csrf()},body});
  let payload={};
  try{payload=await response.json()}catch(_){}
  if(!response.ok||payload.ok===false)throw new Error(payload.error||'Не удалось сохранить');
  return payload;
}

function initDashboard(scope=document){
  const root=scope.id==='dispatcher-day-workspace'?scope:scope.querySelector?.('#dispatcher-day-workspace');
  if(!root||root.dataset.bound==='1')return;
  root.dataset.bound='1';

  const grid=root.querySelector('#route-grid');
  const search=root.querySelector('#route-live-search');
  const state=root.querySelector('#route-state-filter');
  const sort=root.querySelector('#route-sort-filter');

  function applyRouteView(){
    if(!grid)return;
    const q=(search?.value||'').trim().toLowerCase();
    const s=state?.value||'';
    const cards=[...grid.querySelectorAll('.ops-route-card')];
    cards.forEach(card=>{
      const hay=((card.dataset.route||'')+' '+(card.dataset.courier||'')).toLowerCase();
      let stateMismatch=false;
      if(s==='attention')stateMismatch=card.dataset.attention!=='1';
      else if(s==='unassigned')stateMismatch=card.dataset.unassigned!=='1';
      else if(s==='order')stateMismatch=card.dataset.order!=='1';
      else if(s)stateMismatch=card.dataset.state!==s;
      card.classList.toggle('is-hidden',!!((q&&!hay.includes(q))||stateMismatch));
    });
    const mode=sort?.value||'name';
    cards.sort((a,b)=>{
      if(mode==='progress')return Number(a.dataset.percent)-Number(b.dataset.percent)||(a.dataset.route||'').localeCompare(b.dataset.route||'','ru');
      if(mode==='courier')return (a.dataset.courier||'яяя').localeCompare(b.dataset.courier||'яяя','ru')||(a.dataset.route||'').localeCompare(b.dataset.route||'','ru');
      if(mode==='attention')return (a.dataset.attention!=='1')-(b.dataset.attention!=='1')||(a.dataset.route||'').localeCompare(b.dataset.route||'','ru');
      return (a.dataset.route||'').localeCompare(b.dataset.route||'','ru');
    });
    cards.forEach(card=>grid.appendChild(card));
  }

  search?.addEventListener('input',applyRouteView);
  state?.addEventListener('change',applyRouteView);
  sort?.addEventListener('change',applyRouteView);

  root.querySelectorAll('[data-attention-filter]').forEach(link=>link.addEventListener('click',()=>{
    if(state)state.value=link.dataset.attentionFilter||'';
    applyRouteView();
  }));

  root.querySelectorAll('.route-assign-select').forEach(select=>select.addEventListener('change',async()=>{
    if(!select.value)return;
    const card=select.closest('.ops-route-card');
    select.classList.add('is-saving');
    select.disabled=true;
    try{
      const payload=await post(select.dataset.url,{courier_id:select.value});
      const name=payload.courier||select.options[select.selectedIndex]?.textContent||'Курьер назначен';
      const courier=card?.querySelector('.route-courier-name');
      if(courier)courier.textContent=name;
      if(card){
        card.dataset.courier=name.toLowerCase();
        card.dataset.state=payload.state||card.dataset.state;
        card.dataset.attention=payload.needs_attention?'1':'0';
        card.dataset.unassigned='0';
        const badge=card.querySelector('.route-status');
        if(badge){
          const labels={completed:'✓ Завершён',active:'В работе',attention:'Требует внимания',waiting:'Не начат'};
          badge.className='route-status '+card.dataset.state;
          badge.textContent=labels[card.dataset.state]||'Маршрут';
        }
      }
      select.closest('.route-quick-assign')?.remove();
      toast('Курьер назначен');
      applyRouteView();
    }catch(err){
      select.disabled=false;
      select.classList.remove('is-saving');
      toast(err.message,true);
    }
  }));

  root.querySelectorAll('[data-flash]').forEach((node,index)=>{
    setTimeout(()=>toast(node.dataset.flash||node.textContent),index*350);
  });

  applyRouteView();
}

function syncGlobalDate(url){
  const search=document.querySelector('.global-search');
  if(!search)return;
  const value=url.searchParams.get('date')||'';
  let hidden=search.querySelector('input[type=hidden][name=date]');
  if(value&&!hidden){
    hidden=document.createElement('input');
    hidden.type='hidden';
    hidden.name='date';
    search.prepend(hidden);
  }
  if(hidden){
    if(value)hidden.value=value;
    else hidden.remove();
  }
}

let activeDayRequest=null;
async function refreshDashboard(target,{historyMode='push'}={}){
  const url=target instanceof URL?target:new URL(target,window.location.href);
  if(activeDayRequest)activeDayRequest.abort();
  const controller=new AbortController();
  activeDayRequest=controller;
  const current=document.getElementById('dispatcher-day-workspace');
  current?.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},signal:controller.signal});
    if(!response.ok)throw new Error('Не удалось переключить день');
    const html=await response.text();
    if(controller.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('dispatcher-day-workspace');
    if(!fresh)throw new Error('Не удалось обновить диспетчерскую');
    current.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    syncGlobalDate(url);
    initDashboard(fresh);
  }catch(err){
    if(err.name!=='AbortError')toast(err.message,true);
  }finally{
    if(activeDayRequest===controller)activeDayRequest=null;
    document.getElementById('dispatcher-day-workspace')?.classList.remove('is-refreshing');
  }
}

document.addEventListener('click',e=>{
  const link=e.target.closest('[data-live-day][href]');
  if(!link||e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
  e.preventDefault();
  void refreshDashboard(link.href,{historyMode:'push'});
});

window.addEventListener('popstate',()=>{
  if(document.getElementById('dispatcher-day-workspace'))void refreshDashboard(window.location.href,{historyMode:'none'});
});

initDashboard();
