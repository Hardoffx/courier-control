from django.db import models
from django.conf import settings

class Delivery(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В работе'
        DONE = 'done', 'Выполнена'
        PROBLEM = 'problem', 'Проблема'

    delivery_date = models.DateField()
    address = models.CharField(max_length=500)
    organization = models.CharField(max_length=255, blank=True)
    recipient = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    comment = models.TextField(blank=True)
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='deliveries', limit_choices_to={'role':'courier'})
    route_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    problem_reason = models.CharField(max_length=255, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    completed_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('delivery_date', 'courier_id', 'route_order', 'id')

    def __str__(self):
        return f'{self.delivery_date}: {self.address}'

class DeliveryEvent(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=64)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
