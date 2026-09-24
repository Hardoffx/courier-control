import {
  MOTION,
  reduceMotion,
  animateElement,
  bindPressables,
  SingleAccordion,
  warmMotion,
} from "./motion-ui.js";

void warmMotion();

const HOLD_MS=600;
document.querySelectorAll('.hold-done').forEach(btn=>{
  const form=btn.closest('.done-form');
  if(!form)return;
  let timer=null,start=0,armed=false,pointerId=null;
  const fill=btn.querySelector('.hold-fill');
  const reset=()=>{
    if(timer){clearTimeout(timer);timer=null}
    armed=false;start=0;pointerId=null;
    btn.classList.remove('is-holding');
    if(fill){fill.style.transition='none';fill.style.transform='scaleX(0)';requestAnimationFrame(()=>{fill.style.transition=''})}
  };
  const begin=e=>{
    if(btn.disabled||form.dataset.submitting==='1')return;
    if(e.type==='pointerdown'&&e.button!==0)return;
    e.preventDefault();
    pointerId=e.pointerId;
    try{btn.setPointerCapture(pointerId)}catch(_){}
    start=performance.now();armed=false;
    btn.classList.add('is-holding');
    if(fill){fill.style.transition=`transform ${HOLD_MS}ms linear`;requestAnimationFrame(()=>{fill.style.transform='scaleX(1)'})}
    timer=setTimeout(()=>{
      timer=null;armed=true;btn.classList.add('hold-complete');
      if(navigator.vibrate)navigator.vibrate(25);
      form.requestSubmit(btn);
    },HOLD_MS);
  };
  const cancel=e=>{
    if(pointerId!==null&&e.pointerId!==undefined&&e.pointerId!==pointerId)return;
    if(!armed)reset();
  };
  btn.addEventListener('pointerdown',begin);
  btn.addEventListener('pointerup',cancel);
  btn.addEventListener('pointercancel',cancel);
  btn.addEventListener('lostpointercapture',cancel);
  btn.addEventListener('click',e=>{if(!armed)e.preventDefault()});
  btn.addEventListener('contextmenu',e=>e.preventDefault());
});

document.querySelectorAll('.done-form').forEach(f=>f.addEventListener('submit',e=>{
  const btn=f.querySelector('button[type=submit]');
  if(f.dataset.submitting==='1'){e.preventDefault();return}
  if(f.dataset.geo!=='1'&&navigator.geolocation){
    e.preventDefault();
    if(f.dataset.locating==='1')return;
    f.dataset.locating='1';
    if(btn){btn.disabled=true;btn.textContent='✓ Сохраняю…'}
    navigator.geolocation.getCurrentPosition(
      p=>{
        f.querySelector('[name=latitude]').value=p.coords.latitude;
        f.querySelector('[name=longitude]').value=p.coords.longitude;
        f.dataset.geo='1';
        f.dataset.locating='0';
        f.requestSubmit();
      },
      ()=>{
        f.dataset.geo='1';
        f.dataset.locating='0';
        f.requestSubmit();
      },
      {enableHighAccuracy:true,timeout:4000}
    );
    return;
  }
  f.dataset.submitting='1';
  sessionStorage.setItem('courierDoneAt',String(Date.now()));
  const card=f.closest('.selected-card,.route-item');
  const point=card?.querySelector('.next-bar span:last-child,.route-dot')?.textContent?.trim()||'';
  sessionStorage.setItem('courierDonePoint',point);
  const deliveryId=card?.dataset.selectedId||card?.dataset.deliveryId||'';
  if(deliveryId)sessionStorage.setItem('courierDoneId',deliveryId);
  sessionStorage.setItem('courierDoneUrl',f.getAttribute('action')||window.location.href);
  if(btn){btn.disabled=true;const label=btn.querySelector('.hold-label');if(label)label.textContent='✓ Сохраняю…';else btn.textContent='✓ Сохраняю…'}
}));

const doneAt=Number(sessionStorage.getItem('courierDoneAt')||0);
if(doneAt&&Date.now()-doneAt<1800){
  const card=document.querySelector('.selected-card');
  if(card&&!reduceMotion){
    card.classList.remove('just-advanced');
    card.classList.add('completion-highlight');
    setTimeout(()=>card.classList.remove('completion-highlight'),3200);
  }

  const point=sessionStorage.getItem('courierDonePoint')||'';
  const toast=document.createElement('div');
  toast.className='courier-toast';
  const text=document.createElement('span');
  text.textContent='✓ '+(point?'Точка '+point.replace('№','').split(' ')[0]+' выполнена':'Точка выполнена');
  const undo=document.createElement('button');
  undo.type='button';undo.className='toast-undo';undo.textContent='Отменить';
  toast.append(text,undo);
  document.body.appendChild(toast);
  const completedId=sessionStorage.getItem('courierDoneId');
  const completedUrl=sessionStorage.getItem('courierDoneUrl');
  if(completedId&&completedUrl){
    undo.addEventListener('click',()=>{
      undo.disabled=true;undo.textContent='Возвращаю…';
      const token=document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';
      sessionStorage.removeItem('courierDoneAt');sessionStorage.removeItem('courierDonePoint');sessionStorage.removeItem('courierDoneId');sessionStorage.removeItem('courierDoneUrl');
      document.dispatchEvent(new CustomEvent('courier:reopen',{detail:{url:new URL(completedUrl,window.location.href).href,csrf:token}}));
    });
  }else undo.remove();

  sessionStorage.removeItem('courierDoneAt');
  requestAnimationFrame(()=>toast.classList.add('show'));
  setTimeout(()=>{
    toast.classList.remove('show');
    setTimeout(()=>toast.remove(),260);
  },5000);
}

const routeItems=[...document.querySelectorAll('#route-list > .route-list > .route-item')];
const courierAccordion=new SingleAccordion(routeItems);

void bindPressables(document.querySelectorAll('.btn:not(.hold-done),.route-row'));

function openDelivery(id,childId){
  const d=document.getElementById(id);
  if(!d)return;
  if(routeItems.includes(d))courierAccordion.openInstant(d);
  else d.open=true;
  if(childId){
    const c=document.getElementById(childId);
    if(c)c.open=true;
  }
}
document.querySelectorAll('.detail-opener').forEach(a=>a.addEventListener('click',e=>{
  e.preventDefault();
  openDelivery(a.dataset.open,a.dataset.openChild);
}));

document.querySelectorAll('.add-phone-toggle,.phone-editor-toggle,.note-editor-toggle').forEach(btn=>btn.addEventListener('click',()=>{
  const form=document.getElementById(btn.getAttribute('aria-controls'));
  if(!form)return;
  const opening=form.hidden;
  const scope=btn.closest('.compact-top-actions')||btn.closest('.selected-card');
  if(opening&&scope){
    scope.querySelectorAll('.phone-inline-editor,.note-inline-editor,.selected-phone-form').forEach(other=>{
      if(other!==form)other.hidden=true;
    });
    scope.querySelectorAll('.phone-editor-toggle,.note-editor-toggle,.add-phone-toggle').forEach(other=>{
      if(other!==btn){
        other.setAttribute('aria-expanded','false');
        other.classList.remove('is-active');
      }
    });
  }
  form.hidden=!opening;
  btn.setAttribute('aria-expanded',opening?'true':'false');
  btn.classList.toggle('is-active',opening);
  if(opening){
    const input=form.querySelector('input:not([type=hidden])');
    if(input)setTimeout(()=>input.focus(),0);
  }
}));

document.querySelectorAll('.ajax-reorder-form').forEach(form=>form.addEventListener('submit',async e=>{
  e.preventDefault();
  if(form.dataset.busy==='1')return;
  const item=form.closest('.route-item');
  const list=item&&item.parentElement;
  if(!item||!list)return form.submit();

  const direction=form.querySelector('input[name=direction]')?.value;
  const siblings=[...list.children].filter(el=>el.matches('.route-item:not(.done)'));
  const index=siblings.indexOf(item);
  const other=direction==='up'?siblings[index-1]:siblings[index+1];
  if(!other)return;

  form.dataset.busy='1';
  item.classList.add('reorder-moving');
  const rows=[...list.children].filter(el=>el.matches('.route-item'));
  const first=new Map(rows.map(el=>[el,el.getBoundingClientRect()]));

  try{
    const response=await fetch((form.getAttribute('action')||window.location.href),{
      method:'POST',
      body:new FormData(form),
      headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'},
      credentials:'same-origin'
    });
    if(!response.ok)throw new Error((await response.json().catch(()=>({}))).error||'Не удалось изменить порядок');

    if(direction==='up')list.insertBefore(item,other);
    else list.insertBefore(other,item);

    const moved=[...list.children].filter(el=>el.matches('.route-item'));
    await Promise.all(moved.map(async el=>{
      const old=first.get(el);
      if(!old)return;
      const now=el.getBoundingClientRect();
      const dx=old.left-now.left;
      const dy=old.top-now.top;
      if(!dx&&!dy)return;
      await animateElement(el,{
        transform:[`translate(${dx}px,${dy}px)`,'translate(0px,0px)']
      },{duration:.24,ease:MOTION.ease});
      el.style.transform='';
    }));
  }catch(err){
    item.classList.add('reorder-error');
    setTimeout(()=>item.classList.remove('reorder-error'),700);
  }finally{
    form.dataset.busy='0';
    item.classList.remove('reorder-moving');
  }
}));

if(location.hash&&location.hash.startsWith('#delivery-'))openDelivery(location.hash.slice(1));