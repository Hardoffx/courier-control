import os

from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from deliveries.models import (
    Delivery,
    DeliveryEvent,
    DeliveryPoint,
    Route,
    RouteOrderSuggestion,
    RouteRun,
    RouteTemplate,
    RouteTemplateItem,
)


ROUTE_PREFIX = "OPS DEMO · "
USER_PREFIX = "ops-demo-"
POINT_PREFIX = "OPS-"
ROUTE_POINT_COUNTS = (26, 14, 12, 10, 18, 11, 15, 13)
HISTORY_DAYS = 7


class Command(BaseCommand):
    help = (
        "Create a realistic, repeatable multi-route operations dataset for staging "
        "visual acceptance. Use --reset to remove only this scenario."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="target_date",
            help="Scenario day, YYYY-MM-DD. Defaults to today.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove the operations demo dataset instead of creating it.",
        )

    def handle(self, *args, **options):
        if os.getenv("OPERATIONS_DEMO_SEED") != "1":
            raise CommandError(
                "Refusing to modify the database without OPERATIONS_DEMO_SEED=1"
            )
        target_date = self._parse_date(options.get("target_date"))
        if options.get("reset"):
            with transaction.atomic():
                self._reset()
            self.stdout.write(self.style.SUCCESS("Operations demo dataset removed."))
            return

        with transaction.atomic():
            self._reset()
            dispatcher = self._create_dispatcher()
            couriers = self._create_couriers()
            routes = []
            current_runs = []

            for route_index, point_count in enumerate(ROUTE_POINT_COUNTS, start=1):
                courier = None if route_index == 4 else couriers[(route_index - 1) % len(couriers)]
                route, template, points = self._create_route(
                    route_index=route_index,
                    point_count=point_count,
                    courier=courier,
                )
                routes.append(route)

                for day_offset in range(HISTORY_DAYS):
                    run_date = target_date - timedelta(days=day_offset)
                    run = self._create_run(
                        route=route,
                        template=template,
                        points=points,
                        courier=courier,
                        route_index=route_index,
                        run_date=run_date,
                        current_day=(day_offset == 0),
                    )
                    if day_offset == 0:
                        current_runs.append(run)

            self._create_order_suggestion(current_runs[6], couriers[6 % len(couriers)])
            totals = {
                "routes": len(routes),
                "couriers": len(couriers),
                "today": Delivery.objects.filter(
                    delivery_date=target_date,
                    route_run__route__name__startswith=ROUTE_PREFIX,
                ).count(),
                "history": Delivery.objects.filter(
                    route_run__route__name__startswith=ROUTE_PREFIX
                ).count(),
            }

        self.stdout.write(
            self.style.SUCCESS(
                "Operations demo ready: "
                f"{totals['routes']} routes, {totals['couriers']} couriers, "
                f"{totals['today']} deliveries today, {totals['history']} deliveries total."
            )
        )
        self.stdout.write(
            f"Login: {dispatcher.username} / opsdemo12345 · Date: {target_date.isoformat()}"
        )

    def _parse_date(self, raw):
        if not raw:
            return timezone.localdate()
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError("Некорректная дата. Используйте YYYY-MM-DD") from exc

    def _reset(self):
        routes = Route.objects.filter(name__startswith=ROUTE_PREFIX)
        deliveries = Delivery.objects.filter(route_run__route__in=routes)
        DeliveryEvent.objects.filter(delivery__in=deliveries).delete()
        deliveries.delete()
        RouteOrderSuggestion.objects.filter(run__route__in=routes).delete()
        RouteRun.objects.filter(route__in=routes).delete()

        point_ids = list(
            RouteTemplateItem.objects.filter(template__route__in=routes)
            .values_list("point_id", flat=True)
        )
        RouteTemplateItem.objects.filter(template__route__in=routes).delete()
        RouteTemplate.objects.filter(route__in=routes).delete()
        routes.delete()

        DeliveryPoint.objects.filter(pk__in=point_ids, code__startswith=POINT_PREFIX).delete()
        DeliveryPoint.objects.filter(code__startswith=POINT_PREFIX).delete()
        User.objects.filter(username__startswith=USER_PREFIX).delete()

    def _create_dispatcher(self):
        dispatcher = User.objects.create(
            username=f"{USER_PREFIX}dispatcher",
            role=User.Role.DISPATCHER,
            first_name="Мария",
            last_name="Диспетчер",
            is_active=True,
        )
        dispatcher.set_password("opsdemo12345")
        dispatcher.save(update_fields=["password"])
        return dispatcher

    def _create_couriers(self):
        names = (
            ("Алексей", "Соколов", False),
            ("Ирина", "Морозова", False),
            ("Дмитрий", "Кузнецов", False),
            ("Олег", "Волков", True),
            ("Наталья", "Орлова", False),
            ("Максим", "Фёдоров", False),
            ("Антон", "Новиков", True),
            ("Елена", "Павлова", False),
        )
        couriers = []
        for index, (first_name, last_name, reserve) in enumerate(names, start=1):
            courier = User.objects.create(
                username=f"{USER_PREFIX}courier-{index:02d}",
                role=User.Role.COURIER,
                first_name=first_name,
                last_name=last_name,
                phone=f"+79995550{index:03d}",
                is_active=True,
                is_reserve_courier=reserve,
            )
            courier.set_password("opsdemo12345")
            courier.save(update_fields=["password"])
            couriers.append(courier)
        return couriers

    def _create_route(self, *, route_index, point_count, courier):
        route = Route.objects.create(
            name=f"{ROUTE_PREFIX}Маршрут {route_index:02d}",
            default_courier=courier,
            notes="Реалистичный staging-сценарий для визуальной приёмки.",
            is_active=True,
        )
        template = RouteTemplate.objects.create(
            route=route,
            kind=RouteTemplate.Kind.WEEKDAY,
            name="",
            is_active=True,
        )

        points = []
        kinds = (
            DeliveryPoint.Kind.CMD,
            DeliveryPoint.Kind.CMD,
            DeliveryPoint.Kind.INVITRO,
            DeliveryPoint.Kind.EXTERNAL,
            DeliveryPoint.Kind.CMD,
        )
        for position in range(1, point_count + 1):
            kind = kinds[(position - 1) % len(kinds)]
            code = f"{POINT_PREFIX}{route_index:02d}-{position:02d}"
            point = DeliveryPoint.objects.create(
                code=code,
                name=f"Демо точка {route_index:02d}-{position:02d}",
                address=(
                    f"Москва, Демо-проспект {route_index}, дом {position}"
                    if position % 4
                    else f"Москва, Длинное демонстрационное шоссе маршрута {route_index}, дом {position}, корпус 2"
                ),
                kind=kind,
                phone=f"+7999{route_index:02d}{position:05d}",
                is_active=True,
            )
            RouteTemplateItem.objects.create(
                template=template,
                point=point,
                route_order=position,
                enabled_by_default=True,
                time_window=self._time_window(position),
                comment="Забрать документы и расходники" if position % 7 == 0 else "",
            )
            points.append(point)
        return route, template, points

    def _create_run(
        self,
        *,
        route,
        template,
        points,
        courier,
        route_index,
        run_date,
        current_day,
    ):
        statuses = [
            self._current_status(route_index, position, len(points))
            if current_day
            else Delivery.Status.DONE
            for position in range(1, len(points) + 1)
        ]
        assigned = courier if route_index != 4 else None
        run = RouteRun.objects.create(
            route=route,
            template=template,
            run_date=run_date,
            assigned_courier=assigned,
            status=self._run_status(statuses),
        )

        for position, (point, status) in enumerate(zip(points, statuses), start=1):
            completed_at = (
                self._completed_at(run_date, route_index, position)
                if status == Delivery.Status.DONE
                else None
            )
            delivery = Delivery.objects.create(
                delivery_date=run_date,
                route_run=run,
                point=point,
                source_label=point.code,
                address=point.address,
                organization=point.name,
                recipient=f"Получатель {position}",
                phone=point.phone,
                comment="Позвонить за 10 минут" if position % 6 == 0 else "",
                time_window=self._time_window(position),
                courier=assigned,
                route_order=position,
                status=status,
                problem_reason=(
                    "Получатель недоступен"
                    if status == Delivery.Status.PROBLEM
                    else ""
                ),
                completed_at=completed_at,
            )
            if current_day and status == Delivery.Status.DONE:
                DeliveryEvent.objects.create(
                    delivery=delivery,
                    actor=assigned,
                    action="ops_demo_done",
                    note="Демонстрационное выполнение",
                )
            elif current_day and status == Delivery.Status.PROBLEM:
                DeliveryEvent.objects.create(
                    delivery=delivery,
                    actor=assigned,
                    action="ops_demo_problem",
                    note="Получатель недоступен",
                )
        return run

    def _current_status(self, route_index, position, total):
        if route_index in (2, 8):
            return Delivery.Status.DONE
        if route_index == 4 or route_index == 6:
            return Delivery.Status.NEW
        if route_index == 1:
            if position <= 8:
                return Delivery.Status.DONE
            if position == 9:
                return Delivery.Status.IN_PROGRESS
            if position == 10:
                return Delivery.Status.PROBLEM
            return Delivery.Status.NEW
        if route_index == 3:
            if position <= 4:
                return Delivery.Status.DONE
            if position == 5:
                return Delivery.Status.PROBLEM
            return Delivery.Status.NEW
        if route_index == 5:
            if position <= 6:
                return Delivery.Status.DONE
            if position == 7:
                return Delivery.Status.IN_PROGRESS
            return Delivery.Status.NEW
        if route_index == 7:
            if position <= 3:
                return Delivery.Status.DONE
            return Delivery.Status.NEW
        return Delivery.Status.NEW

    def _run_status(self, statuses):
        if statuses and all(status == Delivery.Status.DONE for status in statuses):
            return RouteRun.Status.DONE
        if any(status != Delivery.Status.NEW for status in statuses):
            return RouteRun.Status.IN_PROGRESS
        return RouteRun.Status.READY

    def _time_window(self, position):
        start_hour = 8 + ((position - 1) // 2)
        end_hour = min(start_hour + 2, 23)
        return f"{start_hour:02d}:00-{end_hour:02d}:00"

    def _completed_at(self, run_date, route_index, position):
        naive = datetime.combine(run_date, time(hour=8)) + timedelta(
            minutes=(position * 17) + (route_index * 3)
        )
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _create_order_suggestion(self, run, courier):
        point_order = list(
            run.deliveries.order_by("route_order").values_list("point_id", flat=True)
        )
        proposed = point_order.copy()
        if len(proposed) >= 5:
            proposed[3], proposed[4] = proposed[4], proposed[3]
        RouteOrderSuggestion.objects.create(
            run=run,
            courier=courier,
            original_point_order=point_order,
            proposed_point_order=proposed,
            status=RouteOrderSuggestion.Status.PENDING,
        )
