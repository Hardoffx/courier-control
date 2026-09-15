from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from deliveries import views
from . import pilot_views

urlpatterns = [
    path('healthz/', pilot_views.health, name='health'),
    path('manifest.webmanifest', pilot_views.manifest, name='manifest'),
    path('service-worker.js', pilot_views.service_worker, name='service_worker'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', views.home, name='home'),
    path('dispatcher/', include('deliveries.dispatcher_urls')),
    path('courier/', include('deliveries.courier_urls')),
]
