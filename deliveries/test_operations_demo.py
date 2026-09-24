from io import StringIO
import os

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from unittest.mock import patch

from accounts.models import User
from deliveries.models import Delivery, Route, RouteOrderSuggestion, RouteRun


class OperationsDemoCommandTests(TestCase):
    target_date = "2026-09-24"

    def run_seed(self):
        stdout = StringIO()
        with patch.dict(os.environ, {"OPERATIONS_DEMO_SEED": "1"}):
            call_command(
                "seed_operations_demo",
                target_date=self.target_date,
                stdout=stdout,
            )
        return stdout.getvalue()

    def test_seed_creates_realistic_route_mix_and_is_repeatable(self):
        first_output = self.run_seed()

        routes = Route.objects.filter(name__startswith="OPS DEMO · ")
        self.assertEqual(routes.count(), 8)
        self.assertTrue(
            User.objects.filter(username="ops-demo-dispatcher").exists()
        )
        self.assertEqual(
            User.objects.filter(username__startswith="ops-demo-courier-").count(),
            8,
        )

        today = Delivery.objects.filter(delivery_date=self.target_date)
        self.assertEqual(today.count(), 119)
        self.assertGreater(today.filter(status=Delivery.Status.DONE).count(), 0)
        self.assertGreater(today.filter(status=Delivery.Status.PROBLEM).count(), 0)
        self.assertGreater(today.filter(status=Delivery.Status.IN_PROGRESS).count(), 0)
        self.assertGreater(today.filter(status=Delivery.Status.NEW).count(), 0)

        long_run = RouteRun.objects.get(
            route__name="OPS DEMO · Маршрут 01",
            run_date=self.target_date,
        )
        self.assertEqual(long_run.deliveries.count(), 26)

        unassigned = RouteRun.objects.get(
            route__name="OPS DEMO · Маршрут 04",
            run_date=self.target_date,
        )
        self.assertIsNone(unassigned.assigned_courier)

        suggestion = RouteOrderSuggestion.objects.get(
            run__route__name="OPS DEMO · Маршрут 07",
            run__run_date=self.target_date,
        )
        self.assertEqual(suggestion.status, RouteOrderSuggestion.Status.PENDING)
        self.assertNotEqual(
            suggestion.original_point_order,
            suggestion.proposed_point_order,
        )

        self.assertIn("119 deliveries today", first_output)
        first_total = Delivery.objects.filter(
            route_run__route__name__startswith="OPS DEMO · "
        ).count()

        self.run_seed()
        second_total = Delivery.objects.filter(
            route_run__route__name__startswith="OPS DEMO · "
        ).count()
        self.assertEqual(second_total, first_total)

    def test_reset_removes_only_operations_demo_namespace(self):
        keeper = User.objects.create_user(
            username="real-courier",
            password="pass",
            role=User.Role.COURIER,
        )
        self.run_seed()

        with patch.dict(os.environ, {"OPERATIONS_DEMO_SEED": "1"}):
            call_command("seed_operations_demo", reset=True, stdout=StringIO())

        self.assertFalse(Route.objects.filter(name__startswith="OPS DEMO · ").exists())
        self.assertFalse(
            User.objects.filter(username__startswith="ops-demo-").exists()
        )
        self.assertFalse(
            Delivery.objects.filter(
                route_run__route__name__startswith="OPS DEMO · "
            ).exists()
        )
        self.assertTrue(User.objects.filter(pk=keeper.pk).exists())

    def test_requires_explicit_environment_gate(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesMessage(
                CommandError,
                "OPERATIONS_DEMO_SEED=1",
            ):
                call_command("seed_operations_demo", target_date=self.target_date)

