let activeStatsRequest=null;

function toast(message,error=false){
  let el=document.querySelector('.ops-toast');
  if(!el){el=document.createElement('div');el.className='ops-toast';document.body.appendChild(el)}
  el.textContent=message;
  el.classList.toggle('error',error);
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

function statsUrl(form){
  const url=new URL(window.location.href);
  ['period','from','to'].forEach(key=>url.searchParams.delete(key));
  new FormData(form).forEach((value,key)=>{
    const normalized=String(value).trim();
    if(normalized)url.searchParams.set(key,normalized);
  });
  return url;
}

async function refreshStats(target,{historyMode='replace'}={}){
  const url=target instanceof URL?target:new URL(target,window.location.href);
  if(activeStatsRequest)activeStatsRequest.abort();
  const controller=new AbortController();
  activeStatsRequest=controller;
  const workspace=document.getElementById('stats-live-workspace');
  workspace?.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},signal:controller.signal});
    if(!response.ok)throw new Error('Не удалось обновить статистику');
    const html=await response.text();
    if(controller.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('stats-live-workspace');
    if(!fresh)throw new Error('Не удалось обновить статистику');
    workspace.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    bindStatsControls();
  }catch(err){
    if(err.name!=='AbortError')toast(err.message,true);
  }finally{
    if(activeStatsRequest===controller)activeStatsRequest=null;
    document.getElementById('stats-live-workspace')?.classList.remove('is-refreshing');
  }
}

function bindStatsControls(){
  const form=document.querySelector('.stats-live-filter');
  if(form&&form.dataset.bound!=='1'){
    form.dataset.bound='1';
    form.addEventListener('submit',e=>{
      e.preventDefault();
      void refreshStats(statsUrl(form),{historyMode:'push'});
    });
    form.querySelectorAll('input[type=date]').forEach(input=>input.addEventListener('change',()=>{
      const from=form.querySelector('[name=from]')?.value||'';
      const to=form.querySelector('[name=to]')?.value||'';
      if(from&&to)void refreshStats(statsUrl(form),{historyMode:'replace'});
    }));
  }
  document.querySelectorAll('.stats-live-presets a[href]').forEach(link=>{
    if(link.dataset.bound==='1')return;
    link.dataset.bound='1';
    link.addEventListener('click',e=>{
      if(e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
      e.preventDefault();
      void refreshStats(link.href,{historyMode:'push'});
    });
  });
}
bindStatsControls();

window.addEventListener('popstate',()=>{
  if(document.getElementById('stats-live-workspace'))void refreshStats(window.location.href,{historyMode:'none'});
});
