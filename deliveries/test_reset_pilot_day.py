from datetime import date
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from deliveries.models import Delivery, DeliveryEvent, DeliveryPoint, Route, RouteRun


class ResetPilotDayCommandTests(TestCase):
    def setUp(self):
        self.day = date(2026, 9, 16)
        self.courier = User.objects.create_user(username="courier", password="x")
        self.point = DeliveryPoint.objects.create(
            name="Точка",
            code="458",
            address="Москва, Дубравная, 46",
        )
        self.route = Route.objects.create(name="Тест")
        self.run = RouteRun.objects.create(
            route=self.route,
            run_date=self.day,
            assigned_courier=self.courier,
            status=RouteRun.Status.READY,
        )
        self.original = Delivery.objects.create(
            delivery_date=self.day,
            point=self.point,
            source_label="458",
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.DONE,
            route_order=4,
        )
        self.duplicate = Delivery.objects.create(
            delivery_date=self.day,
            point=self.point,
            route_run=self.run,
            source_label="458",
            address=self.point.address,
            courier=self.courier,
            status=Delivery.Status.IN_PROGRESS,
            route_order=1,
        )
        DeliveryEvent.objects.create(
            delivery=self.original,
            actor=self.courier,
            action="done",
            note="test",
        )

    def test_dry_run_changes_nothing(self):
        output = StringIO()
        call_command("reset_pilot_day", date=self.day.isoformat(), stdout=output)

        self.assertEqual(RouteRun.objects.filter(run_date=self.day).count(), 1)
        self.assertEqual(Delivery.objects.filter(delivery_date=self.day).count(), 2)
        self.assertIn("DRY RUN", output.getvalue())

    def test_apply_removes_runs_duplicates_assignments_and_test_state(self):
        call_command("reset_pilot_day", date=self.day.isoformat(), apply=True)

        self.assertFalse(RouteRun.objects.filter(run_date=self.day).exists())
        rows = list(Delivery.objects.filter(delivery_date=self.day))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIsNone(row.route_run_id)
        self.assertIsNone(row.courier_id)
        self.assertEqual(row.status, Delivery.Status.NEW)
        self.assertEqual(row.route_order, 1)
        self.assertIsNone(row.completed_at)
        self.assertEqual(row.problem_reason, "")
        self.assertFalse(DeliveryEvent.objects.filter(delivery__delivery_date=self.day).exists())
