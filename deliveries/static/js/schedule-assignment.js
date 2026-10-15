// Shared conflict explanation used by every AJAX assignment surface.
window.showScheduleConflict = payload => {
  if(!payload.schedule_url)return;
  let dialog=document.getElementById('schedule-assignment-conflict');
  if(!dialog){
    dialog=document.createElement('dialog');dialog.id='schedule-assignment-conflict';
    dialog.style.cssText='max-width:min(420px,85vw);border:1px solid #c9d7e8;border-radius:14px;padding:20px';
    const title=document.createElement('h2');title.textContent='Проверь график';
    const text=document.createElement('p');text.dataset.conflictText='';
    const link=document.createElement('a');link.className='btn';link.textContent='Открыть график';
    const cancel=document.createElement('button');cancel.type='button';cancel.className='btn alt';cancel.textContent='Отменить';cancel.addEventListener('click',()=>dialog.close());
    dialog.append(title,text,link,cancel);document.body.append(dialog);
  }
  dialog.querySelector('[data-conflict-text]').textContent=payload.error+'. Назначение не сохранено. Отмени выходной в графике, затем повтори назначение.';
  dialog.querySelector('a').href=payload.schedule_url;dialog.showModal();
};
async function refreshScheduleWarnings(){
  const box=document.getElementById('schedule-warnings');if(!box)return;
  try{
    const response=await fetch('/dispatcher/couriers/schedule/warnings/');if(!response.ok)return;
    const payload=await response.json();box.replaceChildren();
    payload.warnings.forEach(w=>{const p=document.createElement('p'),a=document.createElement('a');a.href=w.url;a.textContent=w.text;p.append(a);box.append(p);});
    box.hidden=!payload.warnings.length;
  }catch(_){}
}
window.refreshScheduleWarnings=refreshScheduleWarnings;
let availabilityVersion=0;
async function refreshAssignmentOptions(){
  const form=document.getElementById('generate-route-form');
  const day=form?.querySelector('[name=run_date]')?.value||new URL(location.href).searchParams.get('date')||document.querySelector('[data-run-date]')?.dataset.runDate;
  if(!day)return;
  const version=++availabilityVersion;
  try{
    const response=await fetch('/dispatcher/couriers/schedule/availability/?date='+encodeURIComponent(day));if(!response.ok)return;
    const payload=await response.json();if(version!==availabilityVersion)return;
    document.querySelectorAll('.run-reassign-select,.route-assign-select,#generate-route-form [name=courier_id]').forEach(select=>{
      const current=select.value, first=select.querySelector('option[value=""]')?.cloneNode(true);
      select.replaceChildren();if(first)select.append(first);
      payload.couriers.forEach(c=>{const option=document.createElement('option');option.value=c.id;option.textContent=c.name+c.label;select.append(option);});select.value=current;
    });
  }catch(_){}
}
document.addEventListener('change',e=>{if(e.target.matches('#generate-route-form [name=run_date]'))void refreshAssignmentOptions();});
void refreshAssignmentOptions();

window.addEventListener('pageshow',()=>void refreshScheduleWarnings());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)void refreshScheduleWarnings();});
