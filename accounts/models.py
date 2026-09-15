from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.DISPATCHER)
        extra_fields.setdefault('is_reserve_courier', False)
        return super().create_superuser(username, email=email, password=password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        DISPATCHER = 'dispatcher', 'Диспетчер'
        COURIER = 'courier', 'Курьер'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COURIER)
    phone = models.CharField(max_length=32, blank=True)
    is_reserve_courier = models.BooleanField(default=False, help_text='Резервный курьер без постоянного маршрута; может быть назначен на любой RouteRun')

    objects = UserManager()

    @property
    def is_dispatcher(self):
        return self.is_superuser or self.role == self.Role.DISPATCHER
