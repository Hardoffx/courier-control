from functools import cached_property

from django.db import models
from django.conf import settings

from .lab_catalog import resolve_known_lab


class DeliveryPoint(models.Model):
    class Kind(models.TextChoices):
        CMD='cmd','CMD'; INVITRO='invitro','ИНВИТРО'; EXTERNAL='external','Сторонняя лаборатория'; SERVICE='service','Служебная точка'; UNKNOWN='unknown','Не определено'
    class GeocodeStatus(models.TextChoices):
        PENDING='pending','Ожидает'; OK='ok','Найдена'; FAILED='failed','Не найдена'
    name=models.CharField(max_length=255); code=models.CharField(max_length=100,blank=True); address=models.CharField(max_length=500); kind=models.CharField(max_length=20,choices=Kind.choices,default=Kind.UNKNOWN); phone=models.CharField(max_length=64,blank=True); is_active=models.BooleanField(default=True)
    latitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True); longitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True); geocode_status=models.CharField(max_length=16,choices=GeocodeStatus.choices,default=GeocodeStatus.PENDING); geocoded_address=models.CharField(max_length=500,blank=True); geocoded_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=('kind','name'); constraints=[models.UniqueConstraint(fields=('code','address'),name='unique_point_code_address')]
    def __str__(self): return self.name or self.code or self.address
    def save(self,*args,**kwargs):
        if self.pk:
            previous=type(self).objects.filter(pk=self.pk).values_list('address',flat=True).first()
            if previous is not None and previous!=self.address:
                self.latitude=None; self.longitude=None; self.geocode_status=self.GeocodeStatus.PENDING; self.geocoded_address=''; self.geocoded_at=None
                if kwargs.get('update_fields') is not None:
                    kwargs['update_fields']=set(kwargs['update_fields'])|{'latitude','longitude','geocode_status','geocoded_address','geocoded_at','updated_at'}
        return super().save(*args,**kwargs)


class Route(models.Model):
    name=models.CharField(max_length=120,unique=True)
    default_courier=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='default_routes',limit_choices_to={'role':'courier'})
    is_active=models.BooleanField(default=True)
    notes=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('name',)
    def __str__(self): return self.name


class RouteTemplate(models.Model):
    class Kind(models.TextChoices):
        WEEKDAY='weekday','Будни'; WEEKEND='weekend','Выходные'; CUSTOM='custom','Особый'
    route=models.ForeignKey(Route,on_delete=models.CASCADE,related_name='templates')
    kind=models.CharField(max_length=20,choices=Kind.choices)
    name=models.CharField(max_length=120,blank=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=('route__name','kind','name'); constraints=[models.UniqueConstraint(fields=('route','kind','name'),name='unique_route_template_variant')]
    def __str__(self): return f'{self.route} · {self.name or self.get_kind_display()}'


class RouteTemplateItem(models.Model):
    template=models.ForeignKey(RouteTemplate,on_delete=models.CASCADE,related_name='items')
    point=models.ForeignKey(DeliveryPoint,on_delete=models.PROTECT,related_name='route_template_items')
    route_order=models.PositiveIntegerField(default=0)
    enabled_by_default=models.BooleanField(default=True)
    time_window=models.CharField(max_length=64,blank=True)
    comment=models.CharField(max_length=255,blank=True)
    class Meta:
        ordering=('route_order','id'); constraints=[models.UniqueConstraint(fields=('template','point'),name='unique_point_per_route_template')]
    def __str__(self): return f'{self.template}: {self.route_order}. {self.point}'


class CourierRouteOrderPreference(models.Model):
    template=models.ForeignKey(RouteTemplate,on_delete=models.CASCADE,related_name='courier_order_preferences')
    courier=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='route_order_preferences',limit_choices_to={'role':'courier'})
    point_order=models.JSONField(default=list,blank=True,help_text='Приоритетный порядок точек для этого курьера в этом варианте маршрута')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=('template','courier'),name='unique_courier_order_per_template')]
        ordering=('template__route__name','courier__username')
    def __str__(self): return f'{self.template} · {self.courier}'


class RouteRun(models.Model):
    class Status(models.TextChoices):
        DRAFT='draft','Черновик'; READY='ready','Готов'; IN_PROGRESS='in_progress','В работе'; DONE='done','Завершён'
    route=models.ForeignKey(Route,on_delete=models.PROTECT,related_name='runs')
    template=models.ForeignKey(RouteTemplate,null=True,blank=True,on_delete=models.SET_NULL,related_name='runs')
    run_date=models.DateField()
    assigned_courier=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='route_runs',limit_choices_to={'role':'courier'})
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.DRAFT)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=('-run_date','-created_at','route__name')
    def __str__(self): return f'{self.run_date} · {self.route}'


class RouteOrderSuggestion(models.Model):
    class Status(models.TextChoices):
        PENDING='pending','Ожидает решения'
        APPLIED_TEMPLATE='applied_template','Принят для маршрута'
        APPLIED_COURIER='applied_courier','Сохранён для курьера'
        DISMISSED='dismissed','Только на этот день'
    run=models.OneToOneField(RouteRun,on_delete=models.CASCADE,related_name='order_suggestion')
    courier=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='route_order_suggestions',limit_choices_to={'role':'courier'})
    original_point_order=models.JSONField(default=list,blank=True)
    proposed_point_order=models.JSONField(default=list,blank=True)
    status=models.CharField(max_length=24,choices=Status.choices,default=Status.PENDING)
    decided_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='route_order_decisions')
    decided_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('-updated_at',)
    def __str__(self): return f'{self.run} · {self.get_status_display()}'


class Delivery(models.Model):
    class Status(models.TextChoices):
        NEW='new','Новая'; IN_PROGRESS='in_progress','В работе'; DONE='done','Выполнена'; PROBLEM='problem','Проблема'
    class RowColor(models.TextChoices):
        NONE='','Без цвета'; GREEN='green','Зелёный'; YELLOW='yellow','Жёлтый'; RED='red','Красный'; BLUE='blue','Синий'; GRAY='gray','Серый'
    delivery_date=models.DateField(); route_run=models.ForeignKey(RouteRun,null=True,blank=True,on_delete=models.SET_NULL,related_name='deliveries'); point=models.ForeignKey(DeliveryPoint,null=True,blank=True,on_delete=models.SET_NULL,related_name='deliveries'); source_label=models.CharField(max_length=255,blank=True,help_text='Исходное значение левой колонки'); address=models.CharField(max_length=500); organization=models.CharField(max_length=255,blank=True); recipient=models.CharField(max_length=255,blank=True); phone=models.CharField(max_length=64,blank=True); comment=models.TextField(blank=True); courier_daily_note=models.CharField(max_length=500,blank=True,help_text='Одноразовая заметка курьера только для этой доставки этого дня'); time_window=models.CharField(max_length=64,blank=True); row_color=models.CharField(max_length=16,choices=RowColor.choices,blank=True,default=''); courier=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='deliveries',limit_choices_to={'role':'courier'}); route_order=models.PositiveIntegerField(default=0); status=models.CharField(max_length=20,choices=Status.choices,default=Status.NEW); problem_reason=models.CharField(max_length=255,blank=True); completed_at=models.DateTimeField(null=True,blank=True); completed_latitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True); completed_longitude=models.DecimalField(max_digits=9,decimal_places=6,null=True,blank=True); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=('delivery_date','courier_id','route_order','id')
    def __str__(self): return f'{self.delivery_date}: {self.address}'

    @staticmethod
    def infer_point_kind(label):
        value = (label or '').strip()
        low = value.casefold()
        compact = value.replace('/', '').replace(' ', '')

        if value and compact.isdigit():
            return DeliveryPoint.Kind.CMD

        # «В+» — маркер ветеринарной точки INVITRO в текущем формате.
        if 'в+' in low or 'v+' in low:
            return DeliveryPoint.Kind.INVITRO

        # «МО» здесь — внутренний маркер INVITRO, а не сокращение региона.
        if low.startswith('мо ') or 'инвитро' in low:
            return DeliveryPoint.Kind.INVITRO

        if any(word in low for word in ('склад', 'итого получено', 'ветеринар')):
            return DeliveryPoint.Kind.SERVICE
        if value:
            return DeliveryPoint.Kind.EXTERNAL
        return DeliveryPoint.Kind.UNKNOWN

    @cached_property
    def lab_identity(self):
        known=resolve_known_lab(self.address)
        if known:
            kind=known.kind; code=known.facility_code
        elif self.point_id and self.point:
            kind=self.point.kind; code=self.point.code
        else:
            kind=self.infer_point_kind(self.source_label); code=''
        if kind==DeliveryPoint.Kind.CMD and not code:
            compact=(self.source_label or '').replace('/','').replace(' ','').strip()
            if compact.isdigit(): code=compact
        if kind==DeliveryPoint.Kind.CMD: label='ЦМД'
        elif kind==DeliveryPoint.Kind.INVITRO: label='ИНВИТРО'
        elif kind==DeliveryPoint.Kind.SERVICE: label='Служебная точка'
        elif kind in (DeliveryPoint.Kind.EXTERNAL,DeliveryPoint.Kind.UNKNOWN): label=self.organization or self.source_label or 'Лаборатория'
        else: label=self.organization or self.source_label or 'Точка'
        return {'kind':kind,'code':str(code or '').strip(),'label':label}

    @property
    def lab_kind(self): return self.lab_identity['kind']

    @property
    def lpu_number(self):
        if self.lab_identity['kind']!=DeliveryPoint.Kind.CMD: return ''
        return self.lab_identity['code'].split('/',1)[0].strip()

    @property
    def lab_name(self): return self.lab_identity['label']


class DeliveryEvent(models.Model):
    delivery=models.ForeignKey(Delivery,on_delete=models.CASCADE,related_name='events'); actor=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL); action=models.CharField(max_length=64); note=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
