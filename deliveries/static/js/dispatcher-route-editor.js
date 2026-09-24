import { SingleAccordion, bindPressables, warmMotion } from "./motion-ui.js";

const csrf = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

function toast(message, error=false) {
  let el=document.querySelector('.admin-toast');
  if(!el){el=document.createElement('div');el.className='admin-toast';document.body.appendChild(el)}
  el.textContent=message;
  el.style.background=error?'#8d252b':'';
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);
  el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}

async function post(url, data) {
  const body=data instanceof FormData?data:new URLSearchParams(data);
  const response=await fetch(url,{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':csrf()},body});
  let payload={};
  try{payload=await response.json()}catch(_){}
  if(!response.ok||payload.ok===false) throw new Error(payload.error||'Не удалось сохранить');
  return payload;
}

function renumber(root){
  root.querySelectorAll('.route-editor-item').forEach((item,index)=>{
    const order=item.querySelector('.editor-order');
    if(order) order.textContent=String(index+1);
  });
}

async function saveOrder(root){
  const ids=[...root.querySelectorAll('.route-editor-item')].map(x=>x.dataset.id).filter(Boolean);
  await post(root.dataset.reorderUrl,{order:ids.join(',')});
  renumber(root);
  toast('Порядок сохранён');
}

function clearInsertZones(list){
  list.querySelectorAll('.insert-zone,.move-mode-bar').forEach(x=>x.remove());
  list.classList.remove('is-moving');
  list.querySelectorAll('.is-moving-item').forEach(x=>{
    x.classList.remove('is-moving-item');
    x.removeAttribute('data-move-state');
  });
}

function animateRelocation(item, beforeRect){
  const afterRect=item.getBoundingClientRect();
  const dx=beforeRect.left-afterRect.left;
  const dy=beforeRect.top-afterRect.top;
  if(Math.abs(dx)<1&&Math.abs(dy)<1)return;
  item.animate([
    {transform:`translate(${dx}px,${dy}px)`,zIndex:3},
    {transform:'translate(0,0)',zIndex:3}
  ],{duration:320,easing:'cubic-bezier(.22,1,.36,1)'});
}

function confirmMove(item){
  item.classList.add('move-success');
  item.scrollIntoView({behavior:'smooth',block:'center'});
  toast('Точка перемещена');
  setTimeout(()=>item.classList.remove('move-success'),950);
}

function enterMoveMode(root,item){
  const list=root.querySelector('.route-editor-list');
  clearInsertZones(list);
  item.classList.add('is-moving-item');
  item.dataset.moveState='active';
  list.classList.add('is-moving');

  const bar=document.createElement('div');
  bar.className='move-mode-bar';
  bar.innerHTML='<strong>Выберите новое место</strong><button type="button" class="btn alt move-cancel">Отмена</button>';
  list.prepend(bar);

  const cards=[...list.querySelectorAll('.route-editor-item')].filter(card=>card.dataset.movable!=='0');
  cards.forEach(card=>{
    const zone=document.createElement('button');
    zone.type='button';zone.className='insert-zone';zone.textContent=card===item?'Текущая позиция':'Поставить сюда';
    zone.disabled=card===item;
    zone.addEventListener('click',async()=>{
      const before=item.getBoundingClientRect();
      zone.classList.add('is-chosen');
      list.insertBefore(item,card);
      animateRelocation(item,before);
      clearInsertZones(list);
      try{
        await saveOrder(root);
        confirmMove(item);
      }catch(e){toast(e.message,true);location.reload()}
    });
    list.insertBefore(zone,card);
  });
  const last=document.createElement('button');
  last.type='button';last.className='insert-zone';last.textContent='Поставить в конец';
  last.addEventListener('click',async()=>{
    const before=item.getBoundingClientRect();
    last.classList.add('is-chosen');
    last.parentNode.insertBefore(item,last);
    animateRelocation(item,before);
    clearInsertZones(list);
    try{
      await saveOrder(root);
      confirmMove(item);
    }catch(e){toast(e.message,true);location.reload()}
  });
  const lastMovable=cards[cards.length-1];
  if(lastMovable) lastMovable.after(last); else list.appendChild(last);

  requestAnimationFrame(()=>item.scrollIntoView({behavior:'smooth',block:'center'}));
}

function setupDrag(root){
  const list=root.querySelector('.route-editor-list');
  if(!list) return;
  let dragged=null;
  list.addEventListener('dragstart',e=>{
    const card=e.target.closest('.route-editor-item[data-movable="1"]');
    if(!card||window.matchMedia('(pointer:coarse)').matches)return;
    dragged=card;e.dataTransfer.effectAllowed='move';
  });
  list.addEventListener('dragover',e=>{
    const target=e.target.closest('.route-editor-item[data-movable="1"]');
    if(!dragged||!target||target===dragged)return;
    e.preventDefault();
    const box=target.getBoundingClientRect();
    list.insertBefore(dragged,e.clientY<box.top+box.height/2?target:target.nextSibling);
  });
  list.addEventListener('drop',async e=>{
    if(!dragged)return;e.preventDefault();dragged=null;
    try{await saveOrder(root)}catch(err){toast(err.message,true);location.reload()}
  });
  list.addEventListener('dragend',()=>{dragged=null});
}

function setupEditor(root){
  if(root.dataset.editorReady==='1')return;
  root.dataset.editorReady='1';
  const items=root.querySelectorAll('.route-editor-item');
  const accordion=new SingleAccordion(items,{bodySelector:':scope > .editor-body',summarySelector:':scope > .editor-summary'});
  setupDrag(root);

  root.addEventListener('click',async e=>{
    const interactive=e.target.closest('button,input,select,a,label');
    if(interactive&&interactive.closest('.editor-summary')) e.stopPropagation();

    const move=e.target.closest('.move-start');
    if(move){
      e.preventDefault();
      const card=move.closest('.route-editor-item');
      move.disabled=true;
      try{
        if(card.open) await accordion.transitionTo(card);
        enterMoveMode(root,card);
      }finally{
        move.disabled=false;
      }
      return;
    }

    const cancel=e.target.closest('.move-cancel');
    if(cancel){clearInsertZones(root.querySelector('.route-editor-list'));return}

    const toggle=e.target.closest('.toggle-default');
    if(toggle){
      e.preventDefault();
      try{
        const payload=await post(toggle.dataset.url,{action:'toggle'});
        const card=toggle.closest('.route-editor-item');
        toggle.dataset.enabled=payload.enabled?'1':'0';
        toggle.textContent=payload.enabled?'✓ По умолчанию включена':'— По умолчанию выключена';
        card.classList.toggle('is-disabled',!payload.enabled);
        const defaultMeta=card.querySelector('.meta-default');
        if(defaultMeta) defaultMeta.hidden=payload.enabled;
        toast('Настройка сохранена');
      }catch(err){toast(err.message,true)}
      return;
    }

    const ajaxAction=e.target.closest('.ajax-action');
    if(ajaxAction){
      e.preventDefault();
      try{
        await post(ajaxAction.dataset.url,{action:ajaxAction.dataset.action});
        ajaxAction.disabled=true;
        if(ajaxAction.dataset.action==='unassign') ajaxAction.textContent='Курьер снят';
        toast(ajaxAction.dataset.success||'Изменение сохранено');
        if(root.closest('#run-live-workspace')) await refreshRunWorkspace();
      }catch(err){toast(err.message,true)}
      return;
    }

    const remove=e.target.closest('.remove-item');
    if(remove){
      e.preventDefault();
      if(!confirm(remove.dataset.confirm||'Убрать точку?'))return;
      const card=remove.closest('.route-editor-item');
      try{
        await post(remove.dataset.url,{action:'remove'});
        card.remove();renumber(root);toast('Точка убрана');
        if(root.closest('#run-live-workspace')) await refreshRunWorkspace();
      }catch(err){toast(err.message,true)}
      return;
    }

    const position=e.target.closest('.move-to-position');
    if(position){
      e.preventDefault();
      const card=position.closest('.route-editor-item');
      const input=card.querySelector('.position-input');
      const cards=[...root.querySelectorAll('.route-editor-item')].filter(x=>x.dataset.movable!=='0');
      const raw=parseInt(input?.value||'',10);
      if(!Number.isFinite(raw)){toast('Укажите номер позиции',true);return}
      const n=Math.max(1,Math.min(cards.length,raw));
      const target=cards[n-1];
      if(target!==card){
        if(n>=cards.length) target.after(card);
        else target.parentNode.insertBefore(card,target);
      }
      try{await saveOrder(root)}catch(err){toast(err.message,true);location.reload()}
      return;
    }
  });

  root.querySelectorAll('.inline-edit-form').forEach(form=>{
    const button=form.querySelector('.save-inline');
    const fields=[...form.querySelectorAll('input:not([type=hidden]),textarea')];
    const mark=()=>{if(button){button.hidden=false;button.disabled=false}};
    fields.forEach(f=>f.addEventListener('input',mark));
    form.addEventListener('submit',async e=>{
      e.preventDefault();
      if(button){button.disabled=true;button.textContent='Сохраняю…'}
      try{
        const payload=await post(form.action,new FormData(form));
        const card=form.closest('.route-editor-item');
        const timeMeta=card?.querySelector('.meta-time');
        const commentMeta=card?.querySelector('.meta-comment');
        const timeValue=form.querySelector('[name="time_window"]')?.value.trim()||'';
        const commentValue=form.querySelector('[name="comment"]')?.value.trim()||'';
        if(timeMeta){timeMeta.textContent=timeValue;timeMeta.hidden=!timeValue}
        if(commentMeta){commentMeta.textContent=commentValue?'· '+commentValue:'';commentMeta.hidden=!commentValue}
        if(button){button.hidden=true;button.textContent='Сохранить';button.disabled=false}
        toast('Изменения сохранены');
      }catch(err){
        if(button){button.textContent='Сохранить';button.disabled=false}
        toast(err.message,true);
      }
    });
  });

  root.querySelectorAll('.day-toggle').forEach(x=>x.addEventListener('click',e=>e.stopPropagation()));
}

function initEditors(scope=document){
  scope.querySelectorAll('.admin-route-editor').forEach(setupEditor);
}
initEditors();

document.querySelectorAll('.day-item-toggle').forEach(toggle=>toggle.addEventListener('change',async()=>{
  const form=document.getElementById('generate-route-form');
  const date=form?.querySelector('[name="run_date"]')?.value||'';
  if(!date){
    toggle.checked=!toggle.checked;
    toast('Сначала выберите дату',true);
    return;
  }
  const previous=!toggle.checked;
  toggle.disabled=true;
  toggle.closest('.day-toggle')?.classList.add('is-saving');
  try{
    const payload=await post(toggle.dataset.dayToggleUrl,{run_date:date,enabled:toggle.checked?'1':'0'});
    const label=toggle.closest('.day-toggle')?.querySelector('span');
    if(label)label.textContent=toggle.checked?'В этот день':'Исключена на день';
    toast(payload.message||(toggle.checked?'Точка добавлена':'Точка убрана'));
  }catch(err){
    toggle.checked=previous;
    toast(err.message,true);
  }finally{
    toggle.disabled=false;
    toggle.closest('.day-toggle')?.classList.remove('is-saving');
  }
}));

function bindRunReassign(scope=document){
  scope.querySelectorAll('.run-reassign-select:not([data-bound])').forEach(select=>{
    select.dataset.bound='1';
    select.addEventListener('change',async()=>{
      select.classList.add('is-saving');
      select.disabled=true;
      try{
        const payload=await post(select.dataset.url,{courier_id:select.value});
        const badge=document.querySelector('.route-now-courier');
        if(badge)badge.textContent=payload.courier||'Курьер не назначен';
        toast(payload.message||'Курьер изменён');
        await refreshRunWorkspace();
      }catch(err){
        toast(err.message,true);
      }finally{
        select.disabled=false;
        select.classList.remove('is-saving');
      }
    });
  });
}
bindRunReassign();

document.querySelectorAll('[data-flash]').forEach((node,index)=>setTimeout(()=>toast(node.dataset.flash||node.textContent),index*300));

function bindPointSearch(scope=document){
  scope.querySelectorAll('.point-search:not([data-bound])').forEach(input=>{
    input.dataset.bound='1';
    input.addEventListener('input',()=>{
      const q=input.value.toLowerCase();
      input.closest('form')?.querySelectorAll('.point-option').forEach(row=>{
        row.style.display=row.dataset.search.toLowerCase().includes(q)?'block':'none';
      });
    });
  });
}
bindPointSearch();

async function refreshRunWorkspace(){
  const workspace=document.getElementById('run-live-workspace');
  if(!workspace)return;
  workspace.classList.add('is-refreshing');
  try{
    const response=await fetch(window.location.href,{headers:{'X-Requested-With':'XMLHttpRequest'}});
    if(!response.ok)throw new Error('Не удалось обновить маршрут');
    const html=await response.text();
    const fresh=new DOMParser().parseFromString(html,'text/html').getElementById('run-live-workspace');
    if(!fresh)throw new Error('Не удалось обновить интерфейс маршрута');
    workspace.innerHTML=fresh.innerHTML;
    initEditors(workspace);
    bindRunReassign(workspace);
    bindPointSearch(workspace);
    void bindPressables(workspace.querySelectorAll('.btn,.insert-zone'));
    void warmMotion();
  }finally{
    workspace.classList.remove('is-refreshing');
  }
}

document.addEventListener('submit',async e=>{
  const form=e.target.closest('.ajax-run-form');
  if(!form)return;
  e.preventDefault();
  const question=form.dataset.confirm;
  if(question&&!confirm(question))return;
  const submitter=e.submitter;
  const data=new FormData(form);
  if(submitter?.name)data.append(submitter.name,submitter.value);
  if(submitter)submitter.disabled=true;
  form.classList.add('is-saving');
  try{
    const payload=await post(form.action,data);
    toast(payload.message||'Изменение сохранено');
    if(payload.redirect_url){
      window.location.assign(payload.redirect_url);
      return;
    }
    await refreshRunWorkspace();
  }catch(err){
    toast(err.message,true);
  }finally{
    form.classList.remove('is-saving');
    if(submitter)submitter.disabled=false;
  }
});

void bindPressables(document.querySelectorAll('.btn,.insert-zone'));
void warmMotion();
