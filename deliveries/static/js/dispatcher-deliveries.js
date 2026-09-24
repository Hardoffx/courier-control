const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';

function toast(message,error=false){
  let el=document.querySelector('.ops-toast');
  if(!el){el=document.createElement('div');el.className='ops-toast';document.body.appendChild(el)}
  el.textContent=message;el.classList.toggle('error',error);
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

function checks(){return [...document.querySelectorAll('.row-check')]}
function updateSelected(){
  const n=checks().filter(x=>x.checked).length;
  const el=document.getElementById('selected-count');
  if(el)el.textContent='Выбрано: '+n;
}

function bindSelection(){
  checks().filter(x=>x.dataset.bound!=='1').forEach(x=>{
    x.dataset.bound='1';
    x.addEventListener('change',updateSelected);
  });
  const selectAll=document.getElementById('select-all');
  if(selectAll&&selectAll.dataset.bound!=='1'){
    selectAll.dataset.bound='1';
    selectAll.addEventListener('change',e=>{
      checks().forEach(x=>x.checked=e.target.checked);
      updateSelected();
    });
  }
  updateSelected();
}

function bindBulkForm(){
  const form=document.getElementById('bulk-form');
  if(!form||form.dataset.bound==='1')return;
  form.dataset.bound='1';
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const selected=checks().filter(x=>x.checked);
    if(!selected.length){toast('Сначала выберите доставки',true);return}
    const button=form.querySelector('button[type=submit]');
    const courierSelect=form.querySelector('[name=courier_id]');
    button.disabled=true;
    try{
      const response=await fetch((form.getAttribute('action')||window.location.href),{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':csrf()},body:new FormData(form)});
      const payload=await response.json();
      if(!response.ok||payload.ok===false)throw new Error(payload.error||'Не удалось сохранить');
      const courier=courierSelect.value?courierSelect.options[courierSelect.selectedIndex].textContent:'Курьер не назначен';
      selected.forEach(box=>{
        const id=box.value;
        document.querySelectorAll('[data-delivery-id="'+CSS.escape(id)+'"] .courier-cell').forEach(el=>el.textContent=courier);
        box.checked=false;
      });
      updateSelected();
      toast('Обновлено доставок: '+payload.updated);
    }catch(err){toast(err.message,true)}
    finally{button.disabled=false}
  });
}

function filterUrl(form){
  const url=new URL(window.location.href);
  ['q','route','kind','status','courier'].forEach(key=>url.searchParams.delete(key));
  new FormData(form).forEach((value,key)=>{
    if(key==='date'||String(value).trim())url.searchParams.set(key,String(value));
  });
  if(form.querySelector('[name=route]')?.value)url.searchParams.delete('unrouted');
  return url;
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

let activeFilterRequest=null;
async function refreshDeliveries(target,{historyMode='replace',syncForm=false,fullWorkspace=false}={}){
  const url=target instanceof URL?target:new URL(target,window.location.href);
  if(activeFilterRequest)activeFilterRequest.abort();
  const controller=new AbortController();
  activeFilterRequest=controller;
  const workspace=document.querySelector('.deliveries-workspace');
  workspace?.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},signal:controller.signal});
    if(!response.ok)throw new Error('Не удалось обновить список доставок');
    const html=await response.text();
    if(controller.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html');

    if(fullWorkspace){
      const replacement=fresh.querySelector('.deliveries-workspace');
      if(!workspace||!replacement)throw new Error('Не удалось обновить день');
      workspace.replaceWith(replacement);
    }else{
      for(const selector of ['.delivery-quick','.delivery-panel']){
        const current=document.querySelector(selector);
        const replacement=fresh.querySelector(selector);
        if(current&&replacement)current.replaceWith(replacement);
      }
      if(syncForm){
        const current=document.querySelector('.delivery-filter-card');
        const replacement=fresh.querySelector('.delivery-filter-card');
        if(current&&replacement)current.replaceWith(replacement);
      }
    }

    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    syncGlobalDate(url);
    bindDeliveryWorkspace();
  }catch(err){
    if(err.name!=='AbortError')toast(err.message,true);
  }finally{
    if(activeFilterRequest===controller)activeFilterRequest=null;
    document.querySelector('.deliveries-workspace')?.classList.remove('is-refreshing');
  }
}

let filterTimer=null;
function bindFilters(){
  const form=document.querySelector('.delivery-filter-card');
  if(!form||form.dataset.bound==='1')return;
  form.dataset.bound='1';
  form.addEventListener('submit',e=>{
    e.preventDefault();
    clearTimeout(filterTimer);
    void refreshDeliveries(filterUrl(form),{historyMode:'push'});
  });
  form.querySelector('input[name=q]')?.addEventListener('input',()=>{
    clearTimeout(filterTimer);
    filterTimer=setTimeout(()=>void refreshDeliveries(filterUrl(form),{historyMode:'replace'}),280);
  });
  form.querySelectorAll('select').forEach(select=>select.addEventListener('change',()=>{
    clearTimeout(filterTimer);
    void refreshDeliveries(filterUrl(form),{historyMode:'replace'});
  }));
}

function bindDeliveryWorkspace(){
  bindSelection();
  bindBulkForm();
  bindFilters();
}
bindDeliveryWorkspace();

document.addEventListener('click',e=>{
  const dayLink=e.target.closest('[data-live-delivery-date][href]');
  if(dayLink&&!e.defaultPrevented&&e.button===0&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&!e.altKey){
    e.preventDefault();
    clearTimeout(filterTimer);
    void refreshDeliveries(dayLink.href,{historyMode:'push',fullWorkspace:true});
    return;
  }

  const link=e.target.closest('.delivery-quick a[href],.delivery-filter-card a[href]');
  if(!link||e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
  e.preventDefault();
  clearTimeout(filterTimer);
  void refreshDeliveries(link.href,{historyMode:'push',syncForm:true});
});

window.addEventListener('popstate',()=>{
  clearTimeout(filterTimer);
  void refreshDeliveries(window.location.href,{historyMode:'none',fullWorkspace:true});
});
