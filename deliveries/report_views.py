import csv
from datetime import timedelta
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from accounts.models import User
from .models import Delivery
from .views import dispatcher_required

def _range(request):
    today=timezone.localdate(); preset=request.GET.get('period','7')
    try:
        end=timezone.datetime.strptime(request.GET.get('to',''),'%Y-%m-%d').date() if request.GET.get('to') else today
        start=timezone.datetime.strptime(request.GET.get('from',''),'%Y-%m-%d').date() if request.GET.get('from') else end-timedelta(days=max(1,int(preset))-1)
    except (ValueError,TypeError): start,end=today-timedelta(days=6),today
    if start>end: start,end=end,start
    if (end-start).days>92: start=end-timedelta(days=92)
    return start,end

def _data(start,end):
    base=Delivery.objects.filter(delivery_date__range=(start,end)); total=base.count(); done=base.filter(status=Delivery.Status.DONE).count(); problem=base.filter(status=Delivery.Status.PROBLEM).count()
    couriers=[]
    for courier in User.objects.filter(role=User.Role.COURIER).order_by('first_name','last_name','username'):
        q=base.filter(courier=courier); n=q.count()
        if not n: continue
        d=q.filter(status=Delivery.Status.DONE).count(); p=q.filter(status=Delivery.Status.PROBLEM).count(); couriers.append({'courier':courier,'total':n,'done':d,'problem':p,'rate':round(d*100/n) if n else 0})
    days=[]
    day=start
    while day<=end:
        q=base.filter(delivery_date=day); n=q.count(); d=q.filter(status=Delivery.Status.DONE).count(); p=q.filter(status=Delivery.Status.PROBLEM).count(); days.append({'date':day,'total':n,'done':d,'problem':p,'rate':round(d*100/n) if n else 0}); day+=timedelta(days=1)
    return {'total':total,'done':done,'problem':problem,'rate':round(done*100/total) if total else 0,'couriers':couriers,'days':days}

@dispatcher_required
def management_stats(request):
    start,end=_range(request); data=_data(start,end); data.update({'start':start,'end':end}); return render(request,'dispatcher/stats.html',data)

@dispatcher_required
def management_export(request):
    start,end=_range(request); data=_data(start,end); response=HttpResponse(content_type='text/csv; charset=utf-8'); response['Content-Disposition']=f'attachment; filename="courier-report-{start}-{end}.csv"'; response.write('\ufeff'); writer=csv.writer(response,delimiter=';'); writer.writerow(['Отчёт Courier Control',f'{start} — {end}']); writer.writerow([]); writer.writerow(['Курьер','Всего','Выполнено','Проблемы','Выполнение %'])
    for row in data['couriers']: writer.writerow([row['courier'].get_full_name() or row['courier'].username,row['total'],row['done'],row['problem'],row['rate']])
    writer.writerow([]); writer.writerow(['Дата','Всего','Выполнено','Проблемы','Выполнение %'])
    for row in data['days']: writer.writerow([row['date'].isoformat(),row['total'],row['done'],row['problem'],row['rate']])
    return response
