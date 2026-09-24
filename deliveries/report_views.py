import csv
from statistics import median
from datetime import timedelta
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from accounts.models import User
from .models import Delivery, RouteRun
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

def _duration_label(seconds):
    if seconds is None:
        return '—'
    seconds=max(0,int(seconds))
    hours,rest=divmod(seconds,3600)
    minutes=rest//60
    if hours:
        return f'{hours} ч {minutes:02d} мин' if minutes else f'{hours} ч'
    return f'{minutes} мин' if minutes else '< 1 мин'


def _data(start,end):
    base=Delivery.objects.filter(delivery_date__range=(start,end))
    total=base.count()
    done=base.filter(status=Delivery.Status.DONE).count()
    problem=base.filter(status=Delivery.Status.PROBLEM).count()

    run_times=[]
    run_time_by_courier={}
    run_time_by_day={}
    for run in RouteRun.objects.filter(run_date__range=(start,end)).select_related('route','assigned_courier').prefetch_related('deliveries'):
        rows=list(run.deliveries.all())
        completed=sorted((d for d in rows if d.status==Delivery.Status.DONE and d.completed_at),key=lambda d:d.completed_at)
        if not rows or len(completed)!=len(rows):
            continue
        first=completed[0]
        last=completed[-1]
        seconds=max(0,(last.completed_at-first.completed_at).total_seconds())
        intervals=seconds/(len(completed)-1) if len(completed)>1 else 0
        item={'run':run,'seconds':seconds,'interval_seconds':intervals,'first':first.completed_at,'last':last.completed_at,'points':len(rows)}
        run_times.append(item)
        if run.assigned_courier_id:
            run_time_by_courier.setdefault(run.assigned_courier_id,[]).append(item)
        run_time_by_day.setdefault(run.run_date,[]).append(item)

    durations=[item['seconds'] for item in run_times]
    intervals=[item['interval_seconds'] for item in run_times if item['points']>1]
    avg_duration=sum(durations)/len(durations) if durations else None
    median_duration=median(durations) if durations else None
    avg_interval=sum(intervals)/len(intervals) if intervals else None
    shortest=min(run_times,key=lambda x:x['seconds']) if run_times else None
    longest=max(run_times,key=lambda x:x['seconds']) if run_times else None

    couriers=[]
    for courier in User.objects.filter(role=User.Role.COURIER).order_by('first_name','last_name','username'):
        q=base.filter(courier=courier)
        n=q.count()
        if not n:
            continue
        d=q.filter(status=Delivery.Status.DONE).count()
        p=q.filter(status=Delivery.Status.PROBLEM).count()
        timing=run_time_by_courier.get(courier.pk,[])
        courier_avg=sum(x['seconds'] for x in timing)/len(timing) if timing else None
        couriers.append({
            'courier':courier,'total':n,'done':d,'problem':p,'rate':round(d*100/n) if n else 0,
            'completed_routes':len(timing),'avg_route_duration':_duration_label(courier_avg),
        })

    days=[]
    day=start
    while day<=end:
        q=base.filter(delivery_date=day)
        n=q.count()
        d=q.filter(status=Delivery.Status.DONE).count()
        p=q.filter(status=Delivery.Status.PROBLEM).count()
        timing=run_time_by_day.get(day,[])
        day_avg=sum(x['seconds'] for x in timing)/len(timing) if timing else None
        days.append({
            'date':day,'total':n,'done':d,'problem':p,'rate':round(d*100/n) if n else 0,
            'completed_routes':len(timing),'avg_route_duration':_duration_label(day_avg),
        })
        day+=timedelta(days=1)

    return {
        'total':total,'done':done,'problem':problem,'rate':round(done*100/total) if total else 0,
        'couriers':couriers,'days':days,
        'timing':{
            'completed_routes':len(run_times),
            'avg_duration':_duration_label(avg_duration),
            'median_duration':_duration_label(median_duration),
            'avg_interval':_duration_label(avg_interval),
            'shortest':shortest,
            'longest':longest,
            'shortest_label':_duration_label(shortest['seconds']) if shortest else '—',
            'longest_label':_duration_label(longest['seconds']) if longest else '—',
        },
    }

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
