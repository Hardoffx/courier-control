from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

from .portal import portal_for_request


class PortalLoginView(LoginView):
    template_name = 'registration/login.html'

    def dispatch(self, request, *args, **kwargs):
        portal = portal_for_request(request)
        if request.user.is_authenticated and portal:
            valid = request.user.is_dispatcher if portal == 'control' else not request.user.is_dispatcher
            if valid:
                return redirect('home')
            logout(request)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        portal = portal_for_request(self.request)
        user = form.get_user()
        if portal == 'courier' and user.is_dispatcher:
            form.add_error(None, 'Эта учётная запись предназначена для панели управления.')
            return self.form_invalid(form)
        if portal == 'control' and not user.is_dispatcher:
            form.add_error(None, 'Эта учётная запись предназначена для курьерской панели.')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal = portal_for_request(self.request)
        context['portal'] = portal
        if portal == 'courier':
            context['portal_title'] = 'Вход курьера'
            context['portal_subtitle'] = 'Маршрут и точки доставки'
        elif portal == 'control':
            context['portal_title'] = 'Панель управления'
            context['portal_subtitle'] = 'Диспетчеры и администраторы'
        else:
            context['portal_title'] = 'Вход'
            context['portal_subtitle'] = 'Панель управления доставками'
        return context


class PortalLogoutView(LogoutView):
    pass
