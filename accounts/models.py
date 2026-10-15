from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    tracking_start_date = models.DateField(default=timezone.localdate)
    tracking_end_date = models.DateField(null=True, blank=True)
    schedule_revision = models.PositiveIntegerField(default=0, editable=False)

    def save(self, *args, **kwargs):
        if kwargs.get('update_fields') is not None and not {'tracking_start_date', 'tracking_end_date', 'is_active'}.intersection(kwargs['update_fields']):
            return super().save(*args, **kwargs)
        from django.db import transaction
        from django.db.models import F
        with transaction.atomic():
            old = type(self).objects.filter(pk=self.pk).values('tracking_start_date', 'tracking_end_date').first() if self.pk else None
            if self.pk and not self.is_active and not self.tracking_end_date:
                self.tracking_end_date = timezone.localdate()
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields'] = set(kwargs['update_fields']) | {'tracking_end_date'}
            if old and kwargs.get('update_fields') is None:
                kwargs['update_fields'] = [f.name for f in self._meta.concrete_fields if not f.primary_key and f.name != 'schedule_revision' and f.attname not in self.get_deferred_fields()]
            result = super().save(*args, **kwargs)
            fields = kwargs.get('update_fields')
            if old and any((fields is None or key in fields) and old[key] != getattr(self, key) for key in old):
                type(self).objects.filter(pk=self.pk).update(schedule_revision=F('schedule_revision') + 1)
                from deliveries.schedule_services import audit
                audit(self.pk, 'period', {'before': {k: str(v or '') for k, v in old.items()},
                    'after': {'start': str(self.tracking_start_date), 'end': str(self.tracking_end_date or '')}})
            return result

    class Role(models.TextChoices):
        DISPATCHER = 'dispatcher', 'Диспетчер'
        COURIER = 'courier', 'Курьер'
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COURIER)
    phone = models.CharField(max_length=32, blank=True)
    is_reserve_courier = models.BooleanField(default=False, help_text='Резервный курьер без постоянного маршрута; может быть назначен на любой RouteRun')

    @property
    def is_dispatcher(self):
        return self.is_superuser or self.role == self.Role.DISPATCHER

