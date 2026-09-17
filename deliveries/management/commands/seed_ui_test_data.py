from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = "Create deterministic users for local/CI UI browser tests"

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username="ui_dispatcher",
            defaults={"role": User.Role.DISPATCHER, "is_active": True},
        )
        user.role = User.Role.DISPATCHER
        user.is_active = True
        user.set_password("ui-test-only-password")
        user.save()
        self.stdout.write(self.style.SUCCESS("UI test dispatcher ready"))
