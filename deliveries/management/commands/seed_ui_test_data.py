import os

from django.core.management.base import BaseCommand, CommandError
from accounts.models import User
from django.utils import timezone
from deliveries.models import Delivery, DeliveryPoint, Route, RouteRun, RouteTemplate, RouteTemplateItem


class Command(BaseCommand):
    help = "Create deterministic users for local/CI UI browser tests"

    def handle(self, *args, **options):
        if os.getenv("UI_TESTING") != "1":
            raise CommandError(
                "Refusing to seed deterministic UI credentials without UI_TESTING=1"
            )
        user, _ = User.objects.get_or_create(
            username="ui_dispatcher",
            defaults={"role": User.Role.DISPATCHER, "is_active": True},
        )
        user.role = User.Role.DISPATCHER
        user.is_active = True
        user.set_password("ui-test-only-password")
        user.save()


        courier = None
        if os.getenv("ROUTE_UI_TESTING") == "1" or os.getenv("COURIER_UI_TESTING") == "1":
            courier, _ = User.objects.get_or_create(
                username="ui_courier",
                defaults={"role": User.Role.COURIER, "is_active": True},
            )
            courier.role = User.Role.COURIER
            courier.is_active = True
            courier.set_password("ui-test-only-password")
            courier.save()

        route_name = "UI Test Route"
        if os.getenv("ROUTE_UI_TESTING") == "1":
            courier = User.objects.filter(username="ui_courier").first()
            route, _ = Route.objects.update_or_create(
                pk=910001,
                defaults={"name": route_name, "default_courier": courier, "is_active": True},
            )
            template, _ = RouteTemplate.objects.get_or_create(
                route=route,
                kind=RouteTemplate.Kind.WEEKDAY,
                name="",
            )
            points = []
            for index in range(1, 5):
                point, _ = DeliveryPoint.objects.update_or_create(
                    code=f"UI-{index}",
                    address=f"Москва, Тестовый маршрут, {index}",
                    defaults={
                        "name": f"UI Точка {index}",
                        "kind": DeliveryPoint.Kind.CMD if index < 3 else DeliveryPoint.Kind.INVITRO,
                        "phone": f"+7999000000{index}",
                        "is_active": True,
                    },
                )
                points.append(point)
                RouteTemplateItem.objects.update_or_create(
                    template=template,
                    point=point,
                    defaults={
                        "route_order": index,
                        "enabled_by_default": True,
                        "time_window": f"{8 + index:02d}:00-{9 + index:02d}:00",
                        "comment": "UI regression fixture" if index == 2 else "",
                    },
                )

            run, _ = RouteRun.objects.update_or_create(
                pk=910001,
                defaults={
                    "route": route,
                    "template": template,
                    "run_date": timezone.localdate(),
                    "assigned_courier": courier,
                    "status": RouteRun.Status.READY,
                },
            )

            for index, point in enumerate(points, start=1):
                Delivery.objects.update_or_create(
                    route_run=run,
                    point=point,
                    defaults={
                        "delivery_date": timezone.localdate(),
                        "source_label": point.name,
                        "address": point.address,
                        "phone": point.phone,
                        "courier": courier,
                        "route_order": index,
                        "status": Delivery.Status.NEW,
                        "time_window": f"{8 + index:02d}:00-{9 + index:02d}:00",
                        "comment": "UI regression fixture" if index == 2 else "",
                    },
                )
            self.stdout.write(self.style.SUCCESS("UI route fixture ready"))
        else:
            route = Route.objects.filter(name=route_name).first()
            if route is not None:
                point_ids = list(
                    RouteTemplateItem.objects.filter(template__route=route)
                    .values_list("point_id", flat=True)
                )
                Delivery.objects.filter(route_run__route=route).delete()
                RouteRun.objects.filter(route=route).delete()
                route.delete()
                DeliveryPoint.objects.filter(pk__in=point_ids, code__startswith="UI-").delete()
            self.stdout.write(self.style.SUCCESS("UI route fixture cleared"))

        if os.getenv("COURIER_UI_TESTING") == "1":
            courier, _ = User.objects.get_or_create(
                username="ui_courier",
                defaults={"role": User.Role.COURIER, "is_active": True},
            )
            courier.role = User.Role.COURIER
            courier.is_active = True
            courier.set_password("ui-test-only-password")
            courier.save()

            Delivery.objects.update_or_create(
                delivery_date=timezone.localdate(),
                courier=courier,
                source_label="UI Test Point",
                defaults={
                    "address": "Москва, Тестовая улица, 1",
                    "phone": "+79990000001",
                    "time_window": "10:00-12:00",
                    "route_order": 1,
                    "status": Delivery.Status.IN_PROGRESS,
                    "courier_daily_note": "",
                    "problem_reason": "",
                    "completed_at": None,
                },
            )
            self.stdout.write(self.style.SUCCESS("UI test dispatcher and courier ready"))
        elif os.getenv("ROUTE_UI_TESTING") != "1":
            Delivery.objects.filter(courier__username="ui_courier").delete()
            User.objects.filter(username="ui_courier").delete()
            self.stdout.write(self.style.SUCCESS("UI test dispatcher ready"))
