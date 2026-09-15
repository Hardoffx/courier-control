from django.urls import path
from . import views
urlpatterns = [
 path('', views.dispatcher_dashboard, name='dispatcher_dashboard'),
 path('delivery/new/', views.delivery_create, name='delivery_create'),
 path('delivery/<int:pk>/edit/', views.delivery_edit, name='delivery_edit'),
]
