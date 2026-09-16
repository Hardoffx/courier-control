from django.contrib.auth import logout
from django.http import Http404
from django.shortcuts import redirect

from .portal import portal_for_request, request_host


class PortalHostMiddleware:
    """Hard boundary between courier and control hostnames.

    Nginx separates the public hostnames, but this middleware is the application
    boundary: manually typing an admin/dispatcher URL on the courier hostname (or
    a courier URL on the control hostname) still fails inside Django.
    """

    CONTROL_PREFIXES = ('/admin/', '/dispatcher/')
    COURIER_PREFIXES = ('/courier/',)
    LOCAL_HOSTS = {'127.0.0.1', 'localhost'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        portal = portal_for_request(request)
        host = request_host(request)

        # Local health/deployment checks must keep working with strict mode on.
        if portal is None and host in self.LOCAL_HOSTS:
            return self.get_response(request)

        if portal == 'courier':
            if request.path.startswith(self.CONTROL_PREFIXES):
                raise Http404
            if request.user.is_authenticated and request.user.is_dispatcher:
                logout(request)
                return redirect('login')

        elif portal == 'control':
            if request.path.startswith(self.COURIER_PREFIXES):
                raise Http404
            if request.user.is_authenticated and not request.user.is_dispatcher:
                logout(request)
                return redirect('login')

        elif getattr(request, 'user', None) is not None:
            # With strict split enabled, an unrecognised public hostname should
            # expose no application surface. ALLOWED_HOSTS remains the first line
            # of defence; this also covers legacy names that may still be allowed
            # temporarily during cut-over.
            from django.conf import settings
            if getattr(settings, 'DOMAIN_SPLIT_ENABLED', False):
                raise Http404

        return self.get_response(request)
