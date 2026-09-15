from django.contrib import admin
from .models import Delivery, DeliveryEvent, DeliveryPoint

@admin.register(DeliveryPoint)
class DeliveryPointAdmin(admin.ModelAdmin):
    list_display = ('name','code','kind','address','is_active')
    list_filter = ('kind','is_active')
    search_fields = ('name','code','address','phone')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_date','source_label','address','courier','route_order','time_window','status','completed_at')
    list_filter = ('delivery_date','status','courier','row_color')
    search_fields = ('source_label','address','organization','recipient','phone')

admin.site.register(DeliveryEvent)
