from django.db import models
from django.conf import settings

class DeliveryPoint(models.Model):
    class Kind(models.TextChoices):
        CMD = 'cmd', 'CMD'
        INVITRO = 'invitro', 'ИНВИТРО'
        EXTERNAL = 'external', 'Сторонняя лаборатория'
        SERVICE = 'service', 'Служебная точка'
        UNKNOWN = 'unknown', 'Не определено'

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=500)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.UNKNOWN)
    phone = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('kind','name')
        constraints = [models.UniqueConstraint(fields=('code','address'), name='unique_point_code_address')]

    def __str__(self):
        return self.name or self.code or self.address

class Delivery(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        IN_PROGRESS = 'in_progress', 'В работе'
        DONE = 'done', 'Выполнена'
        PROBLEM = 'problem', 'Проблема'

    class RowColor(models.TextChoices):
        NONE = '', 'Без цвета'
        GREEN = 'green', 'Зелёный'
        YELLOW = 'yellow', 'Жёлтый'
        RED = 'red', 'Красный'
        BLUE = 'blue', 'Синий'
        GRAY = 'gray', 'Серый'

    delivery_date = models.DateField()
    point = models.ForeignKey(DeliveryPoint, null=True, blank=True, on_delete=models.SET_NULL, related_name='deliveries')
    source_label = models.CharField(max_length=255, blank=True, help_text='Исходное значение левой колонки')
    address = models.CharField(max_length=500)
    organization = models.CharField(max_length=255, blank=True)
    recipient = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=64, blank=True)
    comment = models.TextField(blank=True)
    time_window = models.CharField(max_length=64, blank=True)
    row_color = models.CharField(max_length=16, choices=RowColor.choices, blank=True, default='')
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

    @staticmethod
    def infer_point_kind(label):
        value = (label or '').strip()
        low = value.lower()
        compact = value.replace('/','').replace(' ','')
        if value and compact.isdigit():
            return DeliveryPoint.Kind.CMD
        if low.startswith('мо ') or 'инвитро' in low:
            return DeliveryPoint.Kind.INVITRO
        if any(word in low for word in ('склад','итого получено','ветеринар')):
            return DeliveryPoint.Kind.SERVICE
        if value:
            return DeliveryPoint.Kind.EXTERNAL
        return DeliveryPoint.Kind.UNKNOWN

class DeliveryEvent(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=64)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
