from django.urls import path
from . import views, point_views
urlpatterns = [
 path('', views.dispatcher_dashboard, name='dispatcher_dashboard'),
 path('delivery/new/', views.delivery_create, name='delivery_create'),
 path('delivery/<int:pk>/edit/', views.delivery_edit, name='delivery_edit'),
 path('delivery/<int:pk>/quick-edit/', views.dispatcher_quick_edit, name='dispatcher_quick_edit'),
 path('delivery/<int:pk>/assign/', views.dispatcher_assign, name='dispatcher_assign'),
 path('deliveries/bulk-assign/', views.dispatcher_bulk_assign, name='dispatcher_bulk_assign'),
 path('points/', point_views.point_list, name='point_list'),
 path('points/new/', point_views.point_create, name='point_create'),
 path('points/<int:pk>/edit/', point_views.point_edit, name='point_edit'),
 path('points/<int:pk>/toggle/', point_views.point_toggle, name='point_toggle'),
 path('import/', views.import_excel, name='import_excel'),
]
