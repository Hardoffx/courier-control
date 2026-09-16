from django.contrib import admin
from django.urls import include, path
from deliveries import views
from . import pilot_views
from .auth_views import PortalLoginView, PortalLogoutView

urlpatterns = [
    path('healthz/', pilot_views.health, name='health'),
    path('manifest.webmanifest', pilot_views.manifest, name='manifest'),
    path('service-worker.js', pilot_views.service_worker, name='service_worker'),
    path('admin/', admin.site.urls),
    path('login/', PortalLoginView.as_view(), name='login'),
    path('logout/', PortalLogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('dispatcher/', include('deliveries.dispatcher_urls')),
    path('courier/', include('deliveries.courier_urls')),
]
