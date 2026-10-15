from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import RouteRun


@receiver(pre_delete, sender=RouteRun)
def preserve_run_history(sender, instance, **kwargs):
    from .schedule_services import retire_assignment
    retire_assignment(instance)
