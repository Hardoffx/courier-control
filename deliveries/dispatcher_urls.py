from django.urls import path
from . import views, point_views, route_views
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
 path('routes/', route_views.route_list, name='route_list'),
 path('routes/new/', route_views.route_edit, name='route_create'),
 path('routes/<int:pk>/', route_views.route_detail, name='route_detail'),
 path('routes/<int:pk>/edit/', route_views.route_edit, name='route_edit'),
 path('templates/<int:pk>/add-point/', route_views.template_add_point, name='template_add_point'),
 path('template-items/<int:pk>/update/', route_views.template_item_update, name='template_item_update'),
 path('routes/<int:pk>/generate/', route_views.route_generate, name='route_generate'),
 path('runs/<int:pk>/reassign/', route_views.run_reassign, name='run_reassign'),
 path('import/', views.import_excel, name='import_excel'),
]
