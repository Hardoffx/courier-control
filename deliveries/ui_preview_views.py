from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render


@login_required
def ui_preview(request):
    if not request.user.is_dispatcher:
        raise PermissionDenied
    return render(request, "dispatcher/ui_preview.html")
