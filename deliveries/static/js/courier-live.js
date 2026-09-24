import "./courier-bindings.js";

const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
const courierActions=new Set(['done','problem','phone','daily_note','reopen']);
let activeRefresh=null;
let bindingVersion=0;

function liveToast(message,error=false){
  const toast=document.createElement('div');
  toast.className='courier-toast';
  if(error)toast.classList.add('error');
  const text=document.createElement('span');
  text.textContent=message;
  toast.append(text);
  document.body.appendChild(toast);
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(()=>{
    toast.classList.remove('show');
    setTimeout(()=>toast.remove(),260);
  },2600);
}

async function post(url,data,token=csrf()){
  const response=await fetch(url,{
    method:'POST',
    body:data,
    headers:{
      'X-Requested-With':'XMLHttpRequest',
      'X-CSRFToken':token,
      'Accept':'application/json',
    },
    credentials:'same-origin',
  });
  let payload={};
  try{payload=await response.json()}catch(_){}
  if(!response.ok||payload.ok===false)throw new Error(payload.error||'Не удалось сохранить');
  return payload;
}

async function rebindCourierUI(){
  bindingVersion+=1;
  await import(`./courier-bindings.js?live=${bindingVersion}`);
}

async function refreshCourierShell(target=window.location.href,{historyMode='none'}={}){
  const url=target instanceof URL?target:new URL(target,window.location.href);
  if(activeRefresh)activeRefresh.abort();
  const controller=new AbortController();
  activeRefresh=controller;
  const current=document.getElementById('top');
  const openIds=current?[...current.querySelectorAll('details.route-item[open][id]')].map(node=>node.id):[];
  const scrollY=window.scrollY;
  current?.classList.add('is-live-refreshing');
  try{
    const response=await fetch(url,{
      headers:{'X-Requested-With':'XMLHttpRequest'},
      signal:controller.signal,
      credentials:'same-origin',
    });
    if(!response.ok)throw new Error('Не удалось обновить маршрут');
    const html=await response.text();
    if(controller.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('top');
    if(!fresh||!current)throw new Error('Не удалось обновить интерфейс маршрута');
    openIds.forEach(id=>{
      const node=fresh.querySelector('#'+CSS.escape(id));
      if(node)node.open=true;
    });
    current.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    await rebindCourierUI();
    requestAnimationFrame(()=>window.scrollTo({top:scrollY,behavior:'auto'}));
  }catch(err){
    if(err.name!=='AbortError')liveToast(err.message,true);
  }finally{
    if(activeRefresh===controller)activeRefresh=null;
    document.getElementById('top')?.classList.remove('is-live-refreshing');
  }
}

document.addEventListener('submit',async e=>{
  const form=e.target.closest('#top form');
  if(!form||form.matches('.ajax-reorder-form'))return;
  const action=form.querySelector('input[name=action]')?.value||'';
  if(!courierActions.has(action)||e.defaultPrevented)return;
  e.preventDefault();
  if(form.dataset.liveSubmitting==='1')return;
  form.dataset.liveSubmitting='1';
  const button=e.submitter||form.querySelector('button[type=submit]');
  if(button)button.disabled=true;
  try{
    const payload=await post(form.action,new FormData(form));
    const target=new URL(window.location.href);
    if(action==='done'||action==='reopen')target.searchParams.delete('selected');
    await refreshCourierShell(target,{historyMode:'replace'});
    if(action==='phone')liveToast('Телефон сохранён');
    else if(action==='daily_note')liveToast('Заметка сохранена');
    else if(action==='problem')liveToast('Проблема сохранена');
    else if(action==='reopen')liveToast('Точка возвращена в работу');
    else if(payload.message)liveToast(payload.message);
  }catch(err){
    form.dataset.liveSubmitting='0';
    if(button)button.disabled=false;
    liveToast(err.message,true);
  }
});

document.addEventListener('courier:reopen',async e=>{
  const url=e.detail?.url;
  if(!url)return;
  const data=new FormData();
  data.set('action','reopen');
  try{
    await post(url,data,e.detail?.csrf||csrf());
    const target=new URL(window.location.href);
    target.searchParams.delete('selected');
    await refreshCourierShell(target,{historyMode:'replace'});
    liveToast('Точка возвращена в работу');
  }catch(err){
    liveToast(err.message,true);
  }
});

document.addEventListener('click',e=>{
  const link=e.target.closest('#top .selected-nav a[href],#top .route-select-btn[href]');
  if(!link||e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
  const url=new URL(link.href,window.location.href);
  if(!url.searchParams.has('selected'))return;
  e.preventDefault();
  void refreshCourierShell(url,{historyMode:'push'});
});

window.addEventListener('popstate',()=>{
  if(document.getElementById('top'))void refreshCourierShell(window.location.href,{historyMode:'none'});
});
