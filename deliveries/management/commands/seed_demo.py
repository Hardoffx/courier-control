from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from deliveries.models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun

class Command(BaseCommand):
    help='Create/update a compact, repeatable Courier Control presentation dataset.'
    def handle(self,*args,**options):
        dispatcher,_=User.objects.get_or_create(username='demo-dispatcher',defaults={'role':User.Role.DISPATCHER,'first_name':'Анна','last_name':'Диспетчер'}); dispatcher.role=User.Role.DISPATCHER; dispatcher.set_password('demo12345'); dispatcher.save()
        couriers=[]
        for username,first,last,reserve in [('demo-sergey','Сергей','Иванов',False),('demo-andrey','Андрей','Петров',True),('demo-olga','Ольга','Смирнова',False)]:
            user,_=User.objects.get_or_create(username=username,defaults={'role':User.Role.COURIER}); user.role=User.Role.COURIER; user.first_name=first; user.last_name=last; user.is_reserve_courier=reserve; user.is_active=True; user.set_password('demo12345'); user.save(); couriers.append(user)
        points=[]
        samples=[('458','CMD 458','Москва, Митинская улица, 27'),('2939','CMD 2939','Москва, Пятницкое шоссе, 35'),('','ИНВИТРО Митино','Москва, Митинская улица, 57'),('','ЛИТЕХ','Москва, Волоколамское шоссе, 84'),('','ДКЦ','Москва, улица Генерала Белобородова, 19')]
        for code,name,address in samples:
            point,_=DeliveryPoint.objects.get_or_create(code=code,address=address,defaults={'name':name,'kind':DeliveryPoint.Kind.CMD if code else DeliveryPoint.Kind.EXTERNAL}); points.append(point)
        routes=[]
        for i,courier in enumerate(couriers[:2],1): route,_=Route.objects.get_or_create(name=f'DEMO Маршрут {i}',defaults={'default_courier':courier}); routes.append(route)
        today=timezone.localdate()
        for offset in range(7):
            day=today-timedelta(days=offset)
            for ri,route in enumerate(routes):
                courier=couriers[ri]; run,_=RouteRun.objects.get_or_create(route=route,run_date=day,defaults={'assigned_courier':courier,'status':RouteRun.Status.IN_PROGRESS}); run.assigned_courier=courier; run.save(update_fields=['assigned_courier'])
                for pos,point in enumerate(points,1):
                    status=Delivery.Status.DONE
                    if offset==0 and pos==5: status=Delivery.Status.PROBLEM
                    elif offset==0 and pos==4: status=Delivery.Status.IN_PROGRESS
                    delivery,_=Delivery.objects.update_or_create(route_run=run,point=point,defaults={'delivery_date':day,'source_label':point.code or point.name,'address':point.address,'courier':courier,'route_order':pos,'time_window':f'{8+pos:02d}:00','status':status,'problem_reason':'Получатель недоступен' if status==Delivery.Status.PROBLEM else '','completed_at':timezone.now() if status==Delivery.Status.DONE else None})
                    if status==Delivery.Status.DONE: DeliveryEvent.objects.get_or_create(delivery=delivery,action='demo_done',defaults={'actor':courier,'note':'Демонстрационное выполнение'})
        self.stdout.write(self.style.SUCCESS('Demo data ready. Login: demo-dispatcher / demo12345'))
