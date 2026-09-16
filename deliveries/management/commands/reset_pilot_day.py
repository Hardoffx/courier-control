from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from deliveries.models import Delivery, DeliveryEvent, RouteRun


class Command(BaseCommand):
    help = (
        "Reset one pilot day to a clean unassigned state: remove RouteRun rows, "
        "drop duplicate deliveries for the same point, clear test completion/problem "
        "state and events, and keep one delivery row per point."
    )

    def add_arguments(self, parser):
        parser.add_argument("--date", required=True, help="Day to reset, YYYY-MM-DD")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually modify the database. Without this flag the command is dry-run only.",
        )

    def handle(self, *args, **options):
        try:
            target_date = date.fromisoformat(options["date"])
        except ValueError as exc:
            raise CommandError("Некорректная дата. Используйте YYYY-MM-DD") from exc

        deliveries = list(
            Delivery.objects.filter(delivery_date=target_date)
            .select_related("point", "route_run", "courier")
            .order_by("id")
        )
        run_count = RouteRun.objects.filter(run_date=target_date).count()
        event_count = DeliveryEvent.objects.filter(delivery__delivery_date=target_date).count()

        by_point = {}
        duplicate_ids = []
        for delivery in deliveries:
            if not delivery.point_id:
                continue
            if delivery.point_id in by_point:
                duplicate_ids.append(delivery.pk)
            else:
                by_point[delivery.point_id] = delivery.pk

        self.stdout.write(f"Дата: {target_date:%d.%m.%Y}")
        self.stdout.write(f"Маршрутов дня: {run_count}")
        self.stdout.write(f"Доставок дня: {len(deliveries)}")
        self.stdout.write(f"Дублей по точке: {len(duplicate_ids)}")
        self.stdout.write(f"Событий дня: {event_count}")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("DRY RUN: база не изменена. Добавьте --apply для выполнения."))
            return

        with transaction.atomic():
            # RouteRun uses SET_NULL from Delivery, so deleting runs preserves the day rows.
            RouteRun.objects.filter(run_date=target_date).delete()

            # Remove duplicate rows produced by older pilot route generation logic.
            if duplicate_ids:
                Delivery.objects.filter(pk__in=duplicate_ids).delete()

            remaining = list(
                Delivery.objects.filter(delivery_date=target_date).order_by("id")
            )
            for order, delivery in enumerate(remaining, start=1):
                delivery.route_run = None
                delivery.courier = None
                delivery.route_order = order
                delivery.status = Delivery.Status.NEW
                delivery.problem_reason = ""
                delivery.completed_at = None
                delivery.completed_latitude = None
                delivery.completed_longitude = None
                delivery.save(
                    update_fields=[
                        "route_run",
                        "courier",
                        "route_order",
                        "status",
                        "problem_reason",
                        "completed_at",
                        "completed_latitude",
                        "completed_longitude",
                        "updated_at",
                    ]
                )

            DeliveryEvent.objects.filter(delivery__delivery_date=target_date).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {target_date:%d.%m.%Y} очищен. "
                f"Осталось точек: {Delivery.objects.filter(delivery_date=target_date).count()}"
            )
        )
