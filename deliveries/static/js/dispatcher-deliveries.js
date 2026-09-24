const csrf=()=>document.querySelector('[name=csrfmiddlewaretoken]')?.value||'';

function toast(message,error=false){
  let el=document.querySelector('.ops-toast');
  if(!el){el=document.createElement('div');el.className='ops-toast';document.body.appendChild(el)}
  el.textContent=message;el.classList.toggle('error',error);
  requestAnimationFrame(()=>el.classList.add('show'));
  clearTimeout(el._timer);el._timer=setTimeout(()=>el.classList.remove('show'),1800);
}
function checks(){return [...document.querySelectorAll('.row-check')]}
function updateSelected(){const n=checks().filter(x=>x.checked).length;const el=document.getElementById('selected-count');if(el)el.textContent='Выбрано: '+n}
checks().forEach(x=>x.addEventListener('change',updateSelected));
document.getElementById('select-all')?.addEventListener('change',e=>{checks().forEach(x=>x.checked=e.target.checked);updateSelected()});

document.getElementById('bulk-form')?.addEventListener('submit',async e=>{
  e.preventDefault();
  const form=e.currentTarget;
  const selected=checks().filter(x=>x.checked);
  if(!selected.length){toast('Сначала выберите доставки',true);return}
  const button=form.querySelector('button[type=submit]');
  const courierSelect=form.querySelector('[name=courier_id]');
  button.disabled=true;
  try{
    const response=await fetch(form.action,{method:'POST',headers:{'X-Requested-With':'XMLHttpRequest','X-CSRFToken':csrf()},body:new FormData(form)});
    const payload=await response.json();
    if(!response.ok||payload.ok===false)throw new Error(payload.error||'Не удалось сохранить');
    const courier=courierSelect.value?courierSelect.options[courierSelect.selectedIndex].textContent:'Курьер не назначен';
    selected.forEach(box=>{
      const id=box.value;
      document.querySelectorAll('[data-delivery-id="'+CSS.escape(id)+'"] .courier-cell').forEach(el=>el.textContent=courier);
      box.checked=false;
    });
    updateSelected();toast('Обновлено доставок: '+payload.updated);
  }catch(err){toast(err.message,true)}
  finally{button.disabled=false}
});
