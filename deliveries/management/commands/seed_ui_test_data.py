import os

from django.core.management.base import BaseCommand, CommandError
from accounts.models import User
from django.utils import timezone
from deliveries.models import Delivery


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
                },
            )
            self.stdout.write(self.style.SUCCESS("UI test dispatcher and courier ready"))
        else:
            Delivery.objects.filter(courier__username="ui_courier").delete()
            User.objects.filter(username="ui_courier").delete()
            self.stdout.write(self.style.SUCCESS("UI test dispatcher ready"))
