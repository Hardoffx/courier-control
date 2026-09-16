from django.conf import settings


def request_host(request):
    return request.get_host().split(':', 1)[0].lower()


def portal_for_request(request):
    """Return 'courier', 'control', or None for the current host.

    Host separation is intentionally opt-in so local development, CI, and the
    temporary pilot URL keep working until production DNS/HTTPS are ready.
    """
    if not getattr(settings, 'DOMAIN_SPLIT_ENABLED', False):
        return None
    host = request_host(request)
    if host == settings.COURIER_HOST:
        return 'courier'
    if host == settings.CONTROL_HOST:
        return 'control'
    return None
