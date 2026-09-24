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
        long_route_name = "UI Long Route"
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
            long_route, _ = Route.objects.update_or_create(
                pk=910002,
                defaults={"name": long_route_name, "default_courier": courier, "is_active": True},
            )
            long_template, _ = RouteTemplate.objects.get_or_create(
                route=long_route,
                kind=RouteTemplate.Kind.WEEKDAY,
                name="",
            )
            long_points = []
            for index in range(1, 33):
                point, _ = DeliveryPoint.objects.update_or_create(
                    code=f"UI-L-{index:02d}",
                    address=(
                        f"Москва, Длинный тестовый маршрут, дом {index}"
                        if index % 5
                        else f"Москва, Очень длинное название тестового адреса маршрута, дом {index}, корпус 2, строение 1"
                    ),
                    defaults={
                        "name": f"UI Длинная точка {index:02d}",
                        "kind": DeliveryPoint.Kind.CMD if index % 3 else DeliveryPoint.Kind.INVITRO,
                        "phone": f"+7999111{index:04d}",
                        "is_active": True,
                    },
                )
                long_points.append(point)
                RouteTemplateItem.objects.update_or_create(
                    template=long_template,
                    point=point,
                    defaults={
                        "route_order": index,
                        "enabled_by_default": True,
                        "time_window": f"{8 + ((index - 1) // 3):02d}:00-{9 + ((index - 1) // 3):02d}:00",
                        "comment": "Длинный комментарий для проверки переноса текста на мобильном экране" if index % 8 == 0 else "",
                    },
                )

            long_run, _ = RouteRun.objects.update_or_create(
                pk=910002,
                defaults={
                    "route": long_route,
                    "template": long_template,
                    "run_date": timezone.localdate(),
                    "assigned_courier": courier,
                    "status": RouteRun.Status.IN_PROGRESS,
                },
            )
            for index, point in enumerate(long_points, start=1):
                status = Delivery.Status.DONE if index <= 5 else (Delivery.Status.PROBLEM if index == 6 else Delivery.Status.NEW)
                Delivery.objects.update_or_create(
                    route_run=long_run,
                    point=point,
                    defaults={
                        "delivery_date": timezone.localdate(),
                        "source_label": point.name,
                        "address": point.address,
                        "phone": point.phone,
                        "courier": courier,
                        "route_order": index,
                        "status": status,
                        "problem_reason": "Нужно вернуться позже" if status == Delivery.Status.PROBLEM else "",
                        "time_window": f"{8 + ((index - 1) // 3):02d}:00-{9 + ((index - 1) // 3):02d}:00",
                        "comment": "Проверка длинного маршрута" if index % 8 == 0 else "",
                    },
                )
            self.stdout.write(self.style.SUCCESS("UI route fixtures ready"))
        else:
            routes = Route.objects.filter(name__in=(route_name, long_route_name))
            point_ids = list(
                RouteTemplateItem.objects.filter(template__route__in=routes)
                .values_list("point_id", flat=True)
            )
            Delivery.objects.filter(route_run__route__in=routes).delete()
            RouteRun.objects.filter(route__in=routes).delete()
            routes.delete()
            DeliveryPoint.objects.filter(pk__in=point_ids, code__startswith="UI-").delete()
            self.stdout.write(self.style.SUCCESS("UI route fixtures cleared"))

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
