let activePreviewRequest=null;

function showError(message){
  let el=document.querySelector('.preview-toast');
  if(!el){el=document.createElement('div');el.className='preview-toast';document.body.appendChild(el)}
  el.textContent=message;
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

function previewUrl(form){
  const url=new URL(window.location.href);
  url.searchParams.delete('date');
  const date=form.querySelector('[name=date]')?.value||'';
  if(date)url.searchParams.set('date',date);
  return url;
}

async function refreshPreview(target,{historyMode='replace'}={}){
  const url=target instanceof URL?target:new URL(target,window.location.href);
  if(activePreviewRequest)activePreviewRequest.abort();
  const controller=new AbortController();
  activePreviewRequest=controller;
  const workspace=document.getElementById('courier-preview-workspace');
  workspace?.classList.add('is-refreshing');
  try{
    const response=await fetch(url,{headers:{'X-Requested-With':'XMLHttpRequest'},signal:controller.signal});
    if(!response.ok)throw new Error('Не удалось обновить просмотр курьера');
    const html=await response.text();
    if(controller.signal.aborted)return;
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('courier-preview-workspace');
    if(!fresh)throw new Error('Не удалось обновить просмотр курьера');
    workspace.replaceWith(fresh);
    if(historyMode==='push')window.history.pushState({},'',url);
    else if(historyMode==='replace')window.history.replaceState({},'',url);
    bindPreview();
  }catch(err){
    if(err.name!=='AbortError')showError(err.message);
  }finally{
    if(activePreviewRequest===controller)activePreviewRequest=null;
    document.getElementById('courier-preview-workspace')?.classList.remove('is-refreshing');
  }
}

function bindPreview(){
  const form=document.querySelector('.preview-live-date');
  if(!form||form.dataset.bound==='1')return;
  form.dataset.bound='1';
  form.addEventListener('submit',e=>{
    e.preventDefault();
    void refreshPreview(previewUrl(form),{historyMode:'push'});
  });
  form.querySelector('[name=date]')?.addEventListener('change',()=>{
    void refreshPreview(previewUrl(form),{historyMode:'replace'});
  });
}
bindPreview();

window.addEventListener('popstate',()=>{
  if(document.getElementById('courier-preview-workspace'))void refreshPreview(window.location.href,{historyMode:'none'});
});
