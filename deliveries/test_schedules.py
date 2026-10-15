import json
import uuid
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from .models import (CourierAssignment, CourierDayOff, CourierScheduleAudit, Delivery, Route, RouteRun,
                     RouteTemplate, RouteTemplateItem, DeliveryPoint)
from .schedule_services import (ScheduleConflict, availability, month_bounds, month_data, mutate_schedule,
                                replacement_warnings)
from .route_services import generate_route_run, reassign_route_run, dissolve_route_run


class ScheduleTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.courier = User.objects.create_user(username='schedule-ivan', tracking_start_date=self.today-timedelta(days=60))
        self.other = User.objects.create_user(username='schedule-other')
        self.dispatcher = User.objects.create_user(username='schedule-d', role='dispatcher')
        self.route = Route.objects.create(name='Митино', default_courier=self.courier)
        self.client.force_login(self.dispatcher)

    def run_for(self, day, courier=None, route=None):
        return RouteRun.objects.create(route=route or self.route, assigned_courier=courier or self.courier, run_date=day)

    def data(self, day=None, courier=None):
        day = day or self.today
        first,last=month_bounds(day.strftime('%Y-%m'))
        c=courier or self.courier
        c.refresh_from_db()
        return month_data([c],first,last)['rows'][0]

    def status(self, day, courier=None):
        return self.data(day,courier)['days'][day.day-1]['status']

    def change(self, action='off', dates=None, **extra):
        self.courier.refresh_from_db()
        payload={'request_id':str(uuid.uuid4()), 'revision':self.courier.schedule_revision, 'action':action,
                 'dates':[str(d) for d in (dates or [self.today+timedelta(days=1)])], **extra}
        mutate_schedule(self.courier,payload,self.dispatcher)
        return payload

    def test_multiple_runs_and_routes_count_unique_dates(self):
        day=self.today-timedelta(days=1)
        for i in range(3):self.run_for(day)
        self.run_for(day-timedelta(days=1),route=Route.objects.create(name='Второй'))
        row=self.data(day)
        # Avoid crossing a month in assertions about one monthly count.
        self.assertEqual(row['days'][day.day-1]['status'],'worked')
        self.assertEqual(row['days'][day.day-1]['run_count'],3)
        self.assertEqual(len({a.date for a in CourierAssignment.objects.filter(courier=self.courier,active=True)}),2)

    def test_past_off_future_unplanned_and_today_not_worked(self):
        self.assertEqual(self.status(self.today-timedelta(days=1)),'off')
        self.assertEqual(self.status(self.today+timedelta(days=1)),'unplanned')
        self.run_for(self.today)
        self.assertEqual(self.status(self.today),'shift')
        self.assertEqual(self.data()['counts']['worked'],0)
        self.assertEqual(self.data()['counts']['shifts'],1)

    def test_future_off_unique_idempotent_cancellation_and_audit(self):
        payload=self.change(comment='По просьбе')
        mutate_schedule(self.courier,payload,self.dispatcher)
        self.assertEqual(CourierDayOff.objects.count(),1)
        self.assertEqual(CourierScheduleAudit.objects.filter(action='off').count(),1)
        self.assertEqual(self.status(self.today+timedelta(days=1)),'off')
        self.change('cancel')
        self.assertEqual(CourierDayOff.objects.count(),1)
        self.assertFalse(CourierDayOff.objects.get().active)
        self.assertEqual(CourierScheduleAudit.objects.get(action='cancel').actor,self.dispatcher)

    def test_conflict_requires_explicit_decision_atomic_range(self):
        day=self.today+timedelta(days=1)
        self.run_for(day)
        with self.assertRaises(ScheduleConflict):self.change(dates=[day,day+timedelta(days=1)])
        self.assertFalse(CourierDayOff.objects.exists())
        self.change(dates=[day],allow_conflict=True)
        self.assertEqual(self.status(day),'conflict')
        self.assertEqual(self.data(day)['counts']['worked'],0)
        self.change('cancel',dates=[day])
        self.assertEqual(self.status(day),'shift')

    def test_future_reassignment_and_cancellation_do_not_create_work(self):
        day=self.today+timedelta(days=1)
        run=self.run_for(day)
        reassign_route_run(run,self.other)
        self.assertFalse(CourierAssignment.objects.get(courier=self.courier).active)
        with patch('deliveries.schedule_services.timezone.localdate',return_value=day+timedelta(days=1)):
            self.assertEqual(self.status(day),'off')
            self.assertEqual(self.status(day,self.other),'worked')

    def test_historical_reassignment_and_dissolve_preserve_evidence(self):
        day=self.today-timedelta(days=2)
        run=self.run_for(day)
        reassign_route_run(run,self.other)
        self.assertEqual(self.status(day),'worked')
        dissolve_route_run(run)
        self.assertEqual(self.status(day),'worked')
        self.assertEqual(self.status(day,self.other),'worked')
        self.assertIsNone(CourierAssignment.objects.get(courier=self.courier).run_id)
        self.assertEqual(self.data(day)['days'][day.day-1]['routes'][0]['name'],'Митино')

    def test_queryset_delete_retains_history(self):
        day=self.today-timedelta(days=1)
        self.run_for(day)
        RouteRun.objects.all().delete()
        self.assertEqual(self.status(day),'worked')

    def test_today_assignment_survives_reassign_but_is_not_completed_yet(self):
        run=self.run_for(self.today)
        reassign_route_run(run,self.other)
        self.assertEqual(self.data()['counts']['worked'],0)
        with patch('deliveries.schedule_services.timezone.localdate',return_value=self.today+timedelta(days=1)):
            self.assertEqual(self.status(self.today),'worked')

    def test_disabled_courier_keeps_history_and_has_no_post_employment_off(self):
        day=self.today-timedelta(days=1)
        self.run_for(day)
        self.courier.is_active=False
        self.courier.save(update_fields=['is_active'])
        self.assertEqual(self.status(day),'worked')
        self.assertEqual(self.status(self.today+timedelta(days=1)),'outside')

    def test_tracking_start_does_not_invent_past_days(self):
        self.courier.tracking_start_date=self.today
        self.courier.save(update_fields=['tracking_start_date'])
        self.assertEqual(self.status(self.today-timedelta(days=1)),'outside')
        self.run_for(self.today-timedelta(days=2))
        self.assertEqual(self.status(self.today-timedelta(days=2)),'worked')

    def test_audited_history_correction_is_not_overwritten(self):
        day=self.today-timedelta(days=1)
        run=self.run_for(day)
        self.change('correct',dates=[day],worked=False,comment='Ошибочное назначение')
        self.assertEqual(self.status(day),'off')
        run.delete()
        self.assertEqual(self.status(day),'off')
        CourierDayOff.objects.create(courier=self.courier,date=day,active=True)
        self.change('correct',dates=[day],worked=True,comment='Проверили смену')
        self.assertEqual(self.status(day),'worked')
        a=CourierScheduleAudit.objects.filter(action='correct').last()
        self.assertEqual(a.actor,self.dispatcher)
        self.assertTrue(a.details['before'])

    def test_assignment_guard_all_existing_paths(self):
        day=self.today+timedelta(days=1)
        self.change(dates=[day])
        with self.assertRaises(ScheduleConflict):self.run_for(day)
        template=RouteTemplate.objects.create(route=self.route,kind='weekday')
        with self.assertRaises(ScheduleConflict):generate_route_run(template,day)
        run=self.run_for(day,courier=self.other)
        with self.assertRaises(ScheduleConflict):reassign_route_run(run,self.courier)
        with self.assertRaises(ScheduleConflict):Delivery.objects.create(delivery_date=day,courier=self.courier,address='A')
        run.refresh_from_db();self.assertEqual(run.assigned_courier,self.other)
        response=self.client.post(reverse('run_reassign',args=[run.pk]),{'courier_id':self.courier.pk},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,409)
        self.assertIn('schedule_url',response.json())
        response=self.client.post(reverse('route_generate',args=[self.route.pk]),{'template_id':template.pk,'run_date':str(day),'courier_id':self.courier.pk})
        self.assertEqual(response.status_code,409)
        self.assertContains(response,'Открыть график',status_code=409)

    def test_delivery_single_bulk_and_model_forms_cannot_bypass_off(self):
        day=self.today+timedelta(days=1)
        self.change(dates=[day])
        delivery=Delivery.objects.create(delivery_date=day,address='A')
        for url,body in [(reverse('dispatcher_assign',args=[delivery.pk]),{'courier_id':self.courier.pk}),
                         (reverse('dispatcher_bulk_assign'),{'courier_id':self.courier.pk,'delivery_ids':[delivery.pk]}),
                         (reverse('delivery_edit',args=[delivery.pk]),{'delivery_date':str(day),'address':'A','courier':self.courier.pk,'route_order':0,'status':'new','row_color':''})]:
            self.assertEqual(self.client.post(url,body,HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code,409)
        delivery.refresh_from_db();self.assertIsNone(delivery.courier_id)

    def test_courier_access_and_csrf(self):
        self.client.force_login(self.courier)
        for name,args in [('courier_schedule',[self.other.pk]),('courier_schedule_data',[self.other.pk]),('courier_team_schedule',[]),('courier_team_schedule_data',[]),('courier_availability',[]),('courier_schedule_warnings',[])]:
            self.assertEqual(self.client.get(reverse(name,args=args)).status_code,403)
        self.assertEqual(self.client.post(reverse('courier_schedule_change',args=[self.courier.pk]),'{}',content_type='application/json').status_code,403)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.dispatcher)
        self.assertEqual(csrf.post(reverse('courier_schedule_change',args=[self.courier.pk]),'{}',content_type='application/json').status_code,403)
        self.client.force_login(self.dispatcher)
        self.assertEqual(self.client.get(reverse('courier_schedule_change',args=[self.courier.pk])).status_code,405)

    def test_stale_revision_and_reused_request_payload_rejected(self):
        self.courier.refresh_from_db();revision=self.courier.schedule_revision
        payload=self.change()
        stale={**payload,'request_id':str(uuid.uuid4()),'revision':revision,'action':'cancel'}
        with self.assertRaises(ScheduleConflict):mutate_schedule(self.courier,stale,self.dispatcher)
        with self.assertRaises(ScheduleConflict):mutate_schedule(self.courier,{**payload,'action':'cancel'},self.dispatcher)
        self.assertTrue(CourierDayOff.objects.get().active)

    def test_bulk_bounds_bad_json_period_and_history_reason(self):
        for body in ['{','[]','null']:
            self.assertEqual(self.client.post(reverse('courier_schedule_change',args=[self.courier.pk]),body,content_type='application/json').status_code,400)
        with self.assertRaises(ValueError):self.change(dates=[self.today+timedelta(days=i) for i in range(63)])
        with self.assertRaises(ValueError):self.change('period',start='2026-10-20',end='2026-10-19')
        with self.assertRaises(ValueError):self.change('correct',dates=[self.today-timedelta(days=1)],worked=True)

    def test_month_boundaries_leap_year_and_local_date(self):
        for raw,n in [('2024-02',29),('2025-02',28),('2026-04',30),('2026-12',31)]:
            first,last=month_bounds(raw);self.assertEqual(last.day,n)
        first,last=month_bounds('2026-12')
        data=month_data([self.courier],first,last)
        self.assertEqual(data['next'],'2027-01');self.assertEqual(len(data['rows'][0]['days']),31)
        instant=datetime(2026,12,31,22,tzinfo=dt_timezone.utc)
        with patch('django.utils.timezone.now',return_value=instant):
            self.assertEqual(timezone.localdate(),date(2027,1,1))
            self.assertEqual(month_bounds(None)[0],date(2027,1,1))

    def test_batch_queries_do_not_grow_with_team_or_days(self):
        users=[User.objects.create_user(username=f'schedule-load-{i}') for i in range(30)]
        first,last=month_bounds(self.today.strftime('%Y-%m'))
        with self.assertNumQueries(5):month_data(users,first,last)

    def test_warning_and_replacement_resolution(self):
        tomorrow=self.today+timedelta(days=1)
        kind='weekday' if tomorrow.weekday()<5 else ('saturday' if tomorrow.weekday()==5 else 'sunday')
        t=RouteTemplate.objects.create(route=self.route,kind=kind)
        p=DeliveryPoint.objects.create(name='A',address='A')
        RouteTemplateItem.objects.create(template=t,point=p)
        self.change(dates=[tomorrow])
        warnings=replacement_warnings();self.assertEqual(len(warnings),1);self.assertFalse(warnings[0]['confirmed'])
        run=RouteRun.objects.create(route=self.route,run_date=tomorrow)
        self.assertTrue(replacement_warnings()[0]['confirmed'])
        reassign_route_run(run,self.other)
        self.assertEqual(replacement_warnings(),[])
        self.route.is_active=False;self.route.save()
        self.assertEqual(replacement_warnings(),[])

    def test_default_courier_does_not_create_shift_and_multiple_trips_allowed(self):
        self.assertEqual(self.data()['counts']['shifts'],0)
        self.run_for(self.today,courier=self.other)
        self.run_for(self.today,courier=self.other)
        choices=availability([self.courier,self.other],self.today)
        self.assertFalse(any(c.schedule_unavailable for c in choices))


from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class ScheduleMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_routes_deliveries_and_only_surviving_assignments(self):
        executor=MigrationExecutor(connection)
        old=[('deliveries','0008_split_weekend_templates'),('accounts','0002_user_is_reserve_courier')]
        executor.migrate(old)
        apps=executor.loader.project_state(old).apps
        UserOld=apps.get_model('accounts','User')
        RouteOld=apps.get_model('deliveries','Route')
        RunOld=apps.get_model('deliveries','RouteRun')
        DeliveryOld=apps.get_model('deliveries','Delivery')
        user=UserOld.objects.create(username='legacy-schedule',role='courier',is_active=False)
        route=RouteOld.objects.create(name='Legacy')
        past=timezone.localdate()-timedelta(days=10)
        run=RunOld.objects.create(route=route,run_date=past,assigned_courier=user)
        DeliveryOld.objects.create(route_run=run,delivery_date=past,address='A',courier=user)
        try:
            executor=MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            self.assertEqual(RouteRun.objects.filter(pk=run.pk).count(),1)
            self.assertEqual(Delivery.objects.filter(route_run_id=run.pk).count(),1)
            evidence=CourierAssignment.objects.get(courier_id=user.pk)
            self.assertEqual(evidence.date,past);self.assertTrue(evidence.frozen)
            c=User.objects.get(pk=user.pk)
            self.assertEqual(c.tracking_start_date,timezone.localdate())
            self.assertEqual(c.tracking_end_date,timezone.localdate())
            self.assertTrue(CourierScheduleAudit.objects.filter(courier=c,action='legacy_snapshot').exists())
        finally:
            executor=MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
