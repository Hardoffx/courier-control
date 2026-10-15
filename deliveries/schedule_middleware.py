from django.db import OperationalError
from django.http import JsonResponse
from django.shortcuts import render
from .schedule_services import ScheduleConflict, schedule_actor


class ScheduleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        actor = request.user if request.user.is_authenticated else None
        token = schedule_actor.set(actor)
        try:
            return self.get_response(request)
        finally:
            schedule_actor.reset(token)

    def process_exception(self, request, exception):
        if isinstance(exception, OperationalError) and 'locked' in str(exception).lower() and request.path.startswith('/dispatcher/'):
            exception = ScheduleConflict('Данные одновременно меняются. Обновите график и повторите действие.')
        if isinstance(exception, ScheduleConflict):
            payload = exception.payload()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse(payload, status=409)
            return render(request, 'dispatcher/schedule_conflict.html', payload, status=409)
