from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        DISPATCHER = 'dispatcher', 'Диспетчер'
        COURIER = 'courier', 'Курьер'
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COURIER)
    phone = models.CharField(max_length=32, blank=True)
    is_reserve_courier = models.BooleanField(default=False, help_text='Резервный курьер без постоянного маршрута; может быть назначен на любой RouteRun')

    @property
    def is_dispatcher(self):
        return self.is_superuser or self.role == self.Role.DISPATCHER
