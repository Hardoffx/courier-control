from django.contrib import admin
from .models import Delivery, DeliveryEvent

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('delivery_date','address','courier','route_order','status','completed_at')
    list_filter = ('delivery_date','status','courier')
    search_fields = ('address','organization','recipient','phone')

admin.site.register(DeliveryEvent)
