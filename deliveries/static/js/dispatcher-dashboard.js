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

const grid=document.getElementById('route-grid');
const search=document.getElementById('route-live-search');
const state=document.getElementById('route-state-filter');
const sort=document.getElementById('route-sort-filter');

function applyRouteView(){
  if(!grid)return;
  const q=(search?.value||'').trim().toLowerCase();
  const s=state?.value||'';
  const cards=[...grid.querySelectorAll('.ops-route-card')];
  cards.forEach(card=>{
    const hay=(card.dataset.route+' '+card.dataset.courier).toLowerCase();
    const stateMismatch=s==='attention'?card.dataset.attention!=='1':(s&&card.dataset.state!==s);
    card.classList.toggle('is-hidden',!!((q&&!hay.includes(q))||stateMismatch));
  });
  const mode=sort?.value||'name';
  cards.sort((a,b)=>{
    if(mode==='progress')return Number(a.dataset.percent)-Number(b.dataset.percent)||a.dataset.route.localeCompare(b.dataset.route,'ru');
    if(mode==='courier')return (a.dataset.courier||'яяя').localeCompare(b.dataset.courier||'яяя','ru')||a.dataset.route.localeCompare(b.dataset.route,'ru');
    if(mode==='attention')return (a.dataset.attention!=='1')-(b.dataset.attention!=='1')||a.dataset.route.localeCompare(b.dataset.route,'ru');
    return a.dataset.route.localeCompare(b.dataset.route,'ru');
  });
  cards.forEach(card=>grid.appendChild(card));
}
search?.addEventListener('input',applyRouteView);
state?.addEventListener('change',applyRouteView);
sort?.addEventListener('change',applyRouteView);

document.querySelectorAll('[data-attention-filter]').forEach(link=>link.addEventListener('click',()=>{
  if(state)state.value=link.dataset.attentionFilter||'';
  applyRouteView();
}));

document.querySelectorAll('.route-assign-select').forEach(select=>select.addEventListener('change',async()=>{
  if(!select.value)return;
  const card=select.closest('.ops-route-card');
  select.classList.add('is-saving');
  select.disabled=true;
  try{
    const payload=await post(select.dataset.url,{courier_id:select.value});
    const name=payload.courier||select.options[select.selectedIndex]?.textContent||'Курьер назначен';
    const courier=card?.querySelector('.route-courier-name');
    if(courier)courier.textContent=name;
    card.dataset.courier=name.toLowerCase();
    if(card){
      card.dataset.state=payload.state||card.dataset.state;
      card.dataset.attention=payload.needs_attention?'1':'0';
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

document.querySelectorAll('[data-flash]').forEach((node,index)=>{
  setTimeout(()=>toast(node.dataset.flash||node.textContent),index*350);
});

applyRouteView();
