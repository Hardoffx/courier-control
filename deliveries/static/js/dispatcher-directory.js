const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';

function toast(message,error=false){
  let el=document.querySelector('.directory-toast');
  if(!el){el=document.createElement('div');el.className='directory-toast';document.body.appendChild(el)}
  el.textContent=message;
  el.classList.toggle('error',error);
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

async function post(url,data){
  const response=await fetch(url,{
    method:'POST',
    headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':csrf()},
    body:data instanceof FormData?data:new URLSearchParams(data),
  });
  let payload={};
  try{payload=await response.json()}catch(_){}
  if(!response.ok||payload.ok===false)throw new Error(payload.error||'Не удалось сохранить');
  return payload;
}

async function refreshWorkspace(id,url=window.location.href,{historyMode='none'}={}){
  const current=document.getElementById(id);
  if(!current)return;
  current.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'}});
    if(!response.ok)throw new Error('Не удалось обновить список');
    const html=await response.text();
    const freshDoc=new DOMParser().parseFromString(html,'text/html');
    const fresh=freshDoc.getElementById(id);
    if(!fresh)throw new Error('Не удалось обновить интерфейс');
    current.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    bindPointFilters();
  }finally{
    document.getElementById(id)?.classList.remove('is-refreshing');
  }
}

document.addEventListener('submit',async e=>{
  const form=e.target.closest('.ajax-state-toggle');
  if(!form)return;
  e.preventDefault();
  const button=e.submitter||form.querySelector('button[type=submit],button:not([type])');
  if(button)button.disabled=true;
  try{
    const payload=await post((form.getAttribute('action')||window.location.href),new FormData(form));
    toast(payload.message||'Изменение сохранено');
    const workspace=form.closest('#courier-list-workspace,#point-directory-workspace');
    if(workspace)await refreshWorkspace(workspace.id);
  }catch(err){
    toast(err.message,true);
  }finally{
    if(button)button.disabled=false;
  }
});

function pointFilterUrl(form){
  const url=new URL(window.location.href);
  ['q','kind'].forEach(key=>url.searchParams.delete(key));
  new FormData(form).forEach((value,key)=>{
    const normalized=String(value).trim();
    if(normalized)url.searchParams.set(key,normalized);
  });
  return url;
}

let pointFilterTimer=null;
let pointFilterController=null;
async function runPointFilter(form,historyMode='replace'){
  if(pointFilterController)pointFilterController.abort();
  pointFilterController=new AbortController();
  const url=pointFilterUrl(form);
  const workspace=document.getElementById('point-directory-workspace');
  workspace?.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},signal:pointFilterController.signal});
    if(!response.ok)throw new Error('Не удалось обновить справочник');
    const html=await response.text();
    if(pointFilterController.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('point-directory-workspace');
    if(!fresh)throw new Error('Не удалось обновить справочник');
    workspace?.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    bindPointFilters();
  }catch(err){
    if(err.name!=='AbortError')toast(err.message,true);
  }finally{
    document.getElementById('point-directory-workspace')?.classList.remove('is-refreshing');
    pointFilterController=null;
  }
}

function bindPointFilters(){
  const form=document.querySelector('.point-live-filter');
  if(!form||form.dataset.bound==='1')return;
  form.dataset.bound='1';
  form.addEventListener('submit',e=>{
    e.preventDefault();
    clearTimeout(pointFilterTimer);
    void runPointFilter(form,'push');
  });
  form.querySelector('input[name=q]')?.addEventListener('input',()=>{
    clearTimeout(pointFilterTimer);
    pointFilterTimer=setTimeout(()=>void runPointFilter(form,'replace'),280);
  });
  form.querySelector('select[name=kind]')?.addEventListener('change',()=>{
    clearTimeout(pointFilterTimer);
    void runPointFilter(form,'replace');
  });
  form.querySelector('a[href]')?.addEventListener('click',e=>{
    if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
    e.preventDefault();
    clearTimeout(pointFilterTimer);
    void refreshWorkspace('point-directory-workspace',e.currentTarget.href,{historyMode:'push'});
  });
}
bindPointFilters();

window.addEventListener('popstate',()=>{
  if(!document.getElementById('point-directory-workspace'))return;
  clearTimeout(pointFilterTimer);
  void refreshWorkspace('point-directory-workspace',window.location.href);
});
