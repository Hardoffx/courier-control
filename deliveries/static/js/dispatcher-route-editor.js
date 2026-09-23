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
  list.querySelectorAll('.insert-zone').forEach(x=>x.remove());
  list.classList.remove('is-moving');
  list.querySelectorAll('.is-moving-item').forEach(x=>x.classList.remove('is-moving-item'));
}

function enterMoveMode(root,item){
  const list=root.querySelector('.route-editor-list');
  clearInsertZones(list);
  item.classList.add('is-moving-item');
  list.classList.add('is-moving');
  const cards=[...list.querySelectorAll('.route-editor-item')].filter(card=>card.dataset.movable!=='0');
  cards.forEach(card=>{
    const zone=document.createElement('button');
    zone.type='button';zone.className='insert-zone';zone.textContent=card===item?'Текущая позиция':'Поставить сюда';
    zone.disabled=card===item;
    zone.addEventListener('click',async()=>{
      list.insertBefore(item,card);
      clearInsertZones(list);
      try{await saveOrder(root)}catch(e){toast(e.message,true);location.reload()}
    });
    list.insertBefore(zone,card);
  });
  const last=document.createElement('button');
  last.type='button';last.className='insert-zone';last.textContent='Поставить в конец';
  last.addEventListener('click',async()=>{
    list.appendChild(item);
    clearInsertZones(list);
    try{await saveOrder(root)}catch(e){toast(e.message,true);location.reload()}
  });
  const lastMovable=cards[cards.length-1];
  if(lastMovable) lastMovable.after(last); else list.appendChild(last);
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
  const items=root.querySelectorAll('.route-editor-item');
  new SingleAccordion(items,{bodySelector:':scope > .editor-body',summarySelector:':scope > .editor-summary'});
  setupDrag(root);

  root.addEventListener('click',async e=>{
    const interactive=e.target.closest('button,input,select,a,label');
    if(interactive&&interactive.closest('.editor-summary')) e.stopPropagation();

    const move=e.target.closest('.move-start');
    if(move){
      e.preventDefault();
      enterMoveMode(root,move.closest('.route-editor-item'));
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
        await post(form.action,new FormData(form));
        if(button){button.hidden=true;button.textContent='Сохранить';button.disabled=false}
        toast('Изменения сохранены');
      }catch(err){
        if(button){button.textContent='Сохранить';button.disabled=false}
        toast(err.message,true);
      }
    });
  });

  root.querySelectorAll('.day-toggle input').forEach(x=>x.addEventListener('click',e=>e.stopPropagation()));
}

document.querySelectorAll('.admin-route-editor').forEach(setupEditor);
document.querySelectorAll('.point-search').forEach(input=>input.addEventListener('input',()=>{
  const q=input.value.toLowerCase();
  input.closest('form')?.querySelectorAll('.point-option').forEach(row=>{
    row.style.display=row.dataset.search.toLowerCase().includes(q)?'block':'none';
  });
}));
void bindPressables(document.querySelectorAll('.btn,.insert-zone'));
void warmMotion();
