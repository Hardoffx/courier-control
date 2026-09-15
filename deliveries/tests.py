from io import BytesIO
from datetime import timedelta
from openpyxl import Workbook
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from .models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem
from .route_services import generate_route_run, reassign_route_run, learn_template_from_run
from .point_matching import match_point
from .import_services import import_workbook, preview_workbook

class PilotShellTests(TestCase):
    def test_health_checks_database(self):
        response=self.client.get('/healthz/'); self.assertEqual(response.status_code,200); self.assertEqual(response.json()['database'],'ok')
    def test_manifest_is_available(self):
        response=self.client.get('/manifest.webmanifest'); self.assertEqual(response.status_code,200); self.assertEqual(response.json()['display'],'standalone')
    def test_service_worker_is_available(self):
        response=self.client.get('/service-worker.js'); self.assertEqual(response.status_code,200); self.assertIn('javascript',response['Content-Type'])

class DeliveryWorkflowTests(TestCase):
    def setUp(self): self.dispatcher=User.objects.create_user(username='dispatcher',password='pass',role=User.Role.DISPATCHER); self.courier=User.objects.create_user(username='courier',password='pass',role=User.Role.COURIER); self.other=User.objects.create_user(username='other',password='pass',role=User.Role.COURIER); self.delivery=Delivery.objects.create(delivery_date=timezone.localdate(),address='Москва, Тестовая 1',route_order=1)
    def test_point_kind_fallback(self): self.assertEqual(Delivery.infer_point_kind('458'),DeliveryPoint.Kind.CMD); self.assertEqual(Delivery.infer_point_kind('ИНВИТРО Митино'),DeliveryPoint.Kind.INVITRO); self.assertEqual(Delivery.infer_point_kind('Склад'),DeliveryPoint.Kind.SERVICE); self.assertEqual(Delivery.infer_point_kind('ЛИТЕХ'),DeliveryPoint.Kind.EXTERNAL)
    def test_dispatcher_can_assign_courier(self): self.client.login(username='dispatcher',password='pass'); self.client.post(reverse('dispatcher_assign',args=[self.delivery.pk]),{'courier_id':self.courier.pk}); self.delivery.refresh_from_db(); self.assertEqual(self.delivery.courier,self.courier)
    def test_bulk_assignment(self): second=Delivery.objects.create(delivery_date=timezone.localdate(),address='Москва, 2'); self.client.login(username='dispatcher',password='pass'); self.client.post(reverse('dispatcher_bulk_assign'),{'delivery_ids':[self.delivery.pk,second.pk],'courier_id':self.courier.pk}); self.assertEqual(Delivery.objects.filter(pk__in=[self.delivery.pk,second.pk],courier=self.courier).count(),2)
    def test_courier_cannot_complete_another_couriers_delivery(self): self.delivery.courier=self.other; self.delivery.save(); self.client.login(username='courier',password='pass'); self.assertEqual(self.client.post(reverse('courier_update',args=[self.delivery.pk]),{'action':'done'}).status_code,404)
    def test_completion_without_gps_is_allowed(self): self.delivery.courier=self.courier; self.delivery.save(); self.client.login(username='courier',password='pass'); self.client.post(reverse('courier_update',args=[self.delivery.pk]),{'action':'done'}); self.delivery.refresh_from_db(); self.assertEqual(self.delivery.status,Delivery.Status.DONE); self.assertIsNotNone(self.delivery.completed_at)
    def test_completion_with_gps_is_recorded(self): self.delivery.courier=self.courier; self.delivery.save(); self.client.login(username='courier',password='pass'); self.client.post(reverse('courier_update',args=[self.delivery.pk]),{'action':'done','latitude':'55.751244','longitude':'37.618423'}); self.delivery.refresh_from_db(); self.assertEqual(str(self.delivery.completed_latitude),'55.751244'); self.assertTrue(self.delivery.events.filter(action='done',note__icontains='GPS').exists())
    def test_problem_preset_and_comment(self): self.delivery.courier=self.courier; self.delivery.save(); self.client.login(username='courier',password='pass'); self.client.post(reverse('courier_update',args=[self.delivery.pk]),{'action':'problem','problem_reason':'Нет доступа','problem_comment':'охрана не пустила'}); self.delivery.refresh_from_db(); self.assertIn('Нет доступа',self.delivery.problem_reason)
    def test_history_is_dispatcher_only(self): DeliveryEvent.objects.create(delivery=self.delivery,actor=self.dispatcher,action='created',note='test'); self.client.login(username='dispatcher',password='pass'); self.assertEqual(self.client.get(reverse('delivery_history',args=[self.delivery.pk])).status_code,200); self.client.login(username='courier',password='pass'); self.assertEqual(self.client.get(reverse('delivery_history',args=[self.delivery.pk])).status_code,403)
    def test_reorder_renumbers_remaining_route(self): first=self.delivery; first.courier=self.courier; first.save(); second=Delivery.objects.create(delivery_date=timezone.localdate(),address='Москва, Тестовая 2',courier=self.courier,route_order=2); self.client.login(username='courier',password='pass'); self.client.post(reverse('courier_reorder',args=[second.pk]),{'direction':'up'}); first.refresh_from_db(); second.refresh_from_db(); self.assertEqual((second.route_order,first.route_order),(1,2))
    def test_courier_cannot_open_point_directory(self): self.client.login(username='courier',password='pass'); self.assertEqual(self.client.get(reverse('point_list')).status_code,403)

class CourierManagementTests(TestCase):
    def setUp(self): self.dispatcher=User.objects.create_user(username='boss',password='pass',role=User.Role.DISPATCHER); self.client.login(username='boss',password='pass')
    def test_dispatcher_can_create_reserve_courier(self): response=self.client.post(reverse('courier_manage_create'),{'username':'reserve-driver','first_name':'Резерв','password':'temp12345','is_reserve_courier':'on','is_active':'on'}); self.assertEqual(response.status_code,302); self.assertTrue(User.objects.get(username='reserve-driver').is_reserve_courier)
    def test_deactivation_preserves_user(self): courier=User.objects.create_user(username='driver',role=User.Role.COURIER); self.client.post(reverse('courier_manage_toggle',args=[courier.pk])); courier.refresh_from_db(); self.assertFalse(courier.is_active)

class PointImportTests(TestCase):
    def setUp(self): self.dispatcher=User.objects.create_user(username='dispatcher2',role=User.Role.DISPATCHER); self.point=DeliveryPoint.objects.create(name='CMD 458',code='458',address='Москва, Каноническая 10',phone='+79990000000',kind=DeliveryPoint.Kind.CMD)
    def workbook(self,address='Старый адрес',code='458',preamble=False,second_visit=False):
        wb=Workbook(); ws=wb.active
        if preamble: ws.append(['Маршрут курьера на сегодня']); ws.append([])
        ws.append(['Код','Адрес','Время','№']); ws.append([code,address,'09:30',1])
        if second_visit: ws.append([code,address,'17:00',2])
        stream=BytesIO(); wb.save(stream); return stream.getvalue()
    def test_cmd_matches_by_code_before_address(self): self.assertEqual(match_point('458','Совсем другой адрес').point,self.point)
    def test_import_uses_canonical_address_and_phone(self): summary=import_workbook(self.workbook(),self.dispatcher); delivery=Delivery.objects.get(); self.assertEqual(summary.created,1); self.assertEqual(delivery.address,'Москва, Каноническая 10')
    def test_preview_does_not_write_database(self): summary=preview_workbook(self.workbook(code='999',address='Новая точка')); self.assertEqual(summary.new_points,1); self.assertEqual(Delivery.objects.count(),0); self.assertEqual(DeliveryPoint.objects.count(),1)
    def test_reimport_skips_same_row(self): import_workbook(self.workbook(),self.dispatcher); second=import_workbook(self.workbook(),self.dispatcher); self.assertEqual(second.skipped,1)
    def test_header_can_be_below_preamble(self): self.assertEqual(import_workbook(self.workbook(preamble=True),self.dispatcher).created,1)
    def test_same_point_can_be_visited_twice_with_different_slot(self): self.assertEqual(import_workbook(self.workbook(second_visit=True),self.dispatcher).created,2)

class RouteTemplateTests(TestCase):
    def setUp(self):
        self.dispatcher=User.objects.create_user(username='route-dispatcher',password='pass',role=User.Role.DISPATCHER); self.primary=User.objects.create_user(username='primary',role=User.Role.COURIER); self.reserve=User.objects.create_user(username='reserve',role=User.Role.COURIER,is_reserve_courier=True); self.route=Route.objects.create(name='Маршрут 1',default_courier=self.primary); self.weekday=RouteTemplate.objects.create(route=self.route,kind=RouteTemplate.Kind.WEEKDAY); self.weekend=RouteTemplate.objects.create(route=self.route,kind=RouteTemplate.Kind.WEEKEND); self.a=DeliveryPoint.objects.create(name='458',code='458',address='Москва, A',kind=DeliveryPoint.Kind.CMD); self.b=DeliveryPoint.objects.create(name='ИНВИТРО B',address='Москва, B',kind=DeliveryPoint.Kind.INVITRO); RouteTemplateItem.objects.create(template=self.weekday,point=self.a,route_order=1,time_window='09:00'); RouteTemplateItem.objects.create(template=self.weekday,point=self.b,route_order=2,time_window='11:00'); RouteTemplateItem.objects.create(template=self.weekend,point=self.b,route_order=1,time_window='14:00')
    def test_weekday_and_weekend_are_independent(self): self.assertEqual(list(self.weekday.items.values_list('point_id',flat=True)),[self.a.id,self.b.id]); self.assertEqual(list(self.weekend.items.values_list('point_id',flat=True)),[self.b.id])
    def test_generation_uses_default_courier(self): self.assertEqual(generate_route_run(self.weekday,timezone.localdate()).assigned_courier,self.primary)
    def test_reserve_courier_can_take_day_without_changing_template_owner(self): run=generate_route_run(self.weekday,timezone.localdate()); reassign_route_run(run,self.reserve); run.refresh_from_db(); self.route.refresh_from_db(); self.assertEqual(run.assigned_courier,self.reserve); self.assertEqual(self.route.default_courier,self.primary)
    def test_regeneration_does_not_duplicate_points(self): run=generate_route_run(self.weekday,timezone.localdate()); generate_route_run(self.weekday,timezone.localdate()); self.assertEqual(run.deliveries.count(),2)
    def test_regeneration_preserves_completed_delivery(self): run=generate_route_run(self.weekday,timezone.localdate()); done=run.deliveries.get(point=self.a); done.status=Delivery.Status.DONE; done.save(); generate_route_run(self.weekday,timezone.localdate(),enabled_item_ids=[self.weekday.items.get(point=self.b).id]); self.assertTrue(Delivery.objects.filter(pk=done.pk,status=Delivery.Status.DONE).exists())
    def test_dispatcher_can_add_point_only_to_generated_day(self): run=generate_route_run(self.weekday,timezone.localdate()); extra=DeliveryPoint.objects.create(name='ЛИТЕХ',address='Москва, C',kind=DeliveryPoint.Kind.EXTERNAL); count=self.weekday.items.count(); self.client.login(username='route-dispatcher',password='pass'); self.client.post(reverse('run_add_point',args=[run.pk]),{'point_id':extra.pk}); self.assertTrue(run.deliveries.filter(point=extra).exists()); self.assertEqual(self.weekday.items.count(),count)
    def test_batch_template_reorder(self): items=list(self.weekday.items.order_by('route_order')); self.client.login(username='route-dispatcher',password='pass'); self.client.post(reverse('template_reorder',args=[self.weekday.pk]),{'order':f'{items[1].pk},{items[0].pk}'}); self.assertEqual(list(self.weekday.items.order_by('route_order').values_list('point_id',flat=True)),[self.b.pk,self.a.pk])
    def test_batch_run_reorder(self): run=generate_route_run(self.weekday,timezone.localdate()); items=list(run.deliveries.order_by('route_order')); self.client.login(username='route-dispatcher',password='pass'); self.client.post(reverse('run_reorder',args=[run.pk]),{'order':f'{items[1].pk},{items[0].pk}'}); self.assertEqual(list(run.deliveries.order_by('route_order').values_list('point_id',flat=True)),[self.b.pk,self.a.pk])
    def test_copy_previous_route_keeps_today_courier(self): yesterday=timezone.localdate()-timedelta(days=1); old=generate_route_run(self.weekday,yesterday,courier=self.primary); extra=DeliveryPoint.objects.create(name='Extra',address='Москва, C'); Delivery.objects.create(delivery_date=yesterday,route_run=old,point=extra,source_label='Extra',address='Москва, C',courier=self.primary,route_order=3); today=generate_route_run(self.weekday,timezone.localdate(),courier=self.reserve); self.client.login(username='route-dispatcher',password='pass'); self.client.post(reverse('run_copy_previous',args=[today.pk])); self.assertEqual(today.deliveries.count(),3); self.assertFalse(today.deliveries.exclude(courier=self.reserve).exists())
    def test_learning_actual_day_updates_only_selected_template(self):
        run=generate_route_run(self.weekday,timezone.localdate()); extra=DeliveryPoint.objects.create(name='Extra',address='Москва, C'); Delivery.objects.create(delivery_date=run.run_date,route_run=run,point=extra,source_label='Extra',address=extra.address,route_order=3,time_window='18:00'); weekend_before=list(self.weekend.items.values_list('point_id','route_order','time_window')); count=learn_template_from_run(run,self.weekday); self.assertEqual(count,3); self.assertEqual(list(self.weekday.items.order_by('route_order').values_list('point_id',flat=True)),[self.a.pk,self.b.pk,extra.pk]); self.assertEqual(list(self.weekend.items.values_list('point_id','route_order','time_window')),weekend_before)
    def test_learning_rejects_template_from_other_route(self):
        run=generate_route_run(self.weekday,timezone.localdate()); other_route=Route.objects.create(name='Другой'); other_template=RouteTemplate.objects.create(route=other_route,kind=RouteTemplate.Kind.WEEKDAY)
        with self.assertRaises(ValueError): learn_template_from_run(run,other_template)
