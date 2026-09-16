from django.contrib import admin
from .models import (
    CourierRouteOrderPreference,
    Delivery,
    DeliveryEvent,
    DeliveryPoint,
    Route,
    RouteOrderSuggestion,
    RouteRun,
    RouteTemplate,
    RouteTemplateItem,
)

@admin.register(DeliveryPoint)
class DeliveryPointAdmin(admin.ModelAdmin):
    list_display=('name','code','kind','address','is_active'); list_filter=('kind','is_active'); search_fields=('name','code','address','phone')

class RouteTemplateItemInline(admin.TabularInline):
    model=RouteTemplateItem; extra=0; ordering=('route_order',); autocomplete_fields=('point',)

@admin.register(RouteTemplate)
class RouteTemplateAdmin(admin.ModelAdmin):
    list_display=('route','kind','name','is_active'); list_filter=('kind','is_active'); inlines=(RouteTemplateItemInline,)

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display=('name','default_courier','is_active'); list_filter=('is_active',); search_fields=('name','default_courier__username','default_courier__first_name')

@admin.register(RouteRun)
class RouteRunAdmin(admin.ModelAdmin):
    list_display=('run_date','route','template','assigned_courier','status'); list_filter=('run_date','status','route'); search_fields=('route__name','assigned_courier__username')

@admin.register(CourierRouteOrderPreference)
class CourierRouteOrderPreferenceAdmin(admin.ModelAdmin):
    list_display=('template','courier','updated_at'); list_filter=('template__route',); search_fields=('template__route__name','courier__username','courier__first_name')

@admin.register(RouteOrderSuggestion)
class RouteOrderSuggestionAdmin(admin.ModelAdmin):
    list_display=('run','courier','status','updated_at','decided_by'); list_filter=('status','run__route'); search_fields=('run__route__name','courier__username')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display=('delivery_date','source_label','address','courier','route_run','route_order','time_window','status','completed_at'); list_filter=('delivery_date','status','courier','row_color'); search_fields=('source_label','address','organization','recipient','phone')

admin.site.register(DeliveryEvent)
