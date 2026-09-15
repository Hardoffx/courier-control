from django.urls import path
from . import views
urlpatterns = [
 path('', views.courier_today, name='courier_today'),
 path('delivery/<int:pk>/update/', views.courier_update, name='courier_update'),
 path('delivery/<int:pk>/reorder/', views.courier_reorder, name='courier_reorder'),
]
