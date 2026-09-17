from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        tables = set(connection.introspection.table_names())
        required = {'django_migrations', 'accounts_user', 'deliveries_delivery'}
        if not required.issubset(tables):
            return JsonResponse({'status':'error','database':'ok','schema':'error'}, status=503)
        return JsonResponse({'status':'ok','database':'ok','schema':'ok'})
    except Exception:
        return JsonResponse({'status':'error','database':'error','schema':'unknown'}, status=503)


def manifest(request):
    return JsonResponse({
        'name':'Courier Control', 'short_name':'Courier', 'start_url':'/', 'scope':'/',
        'display':'standalone', 'background_color':'#f4f6f8', 'theme_color':'#111827',
        'description':'Маршруты и рабочий экран курьера'
    }, content_type='application/manifest+json')


@never_cache
def service_worker(request):
    # Transitional cleanup worker: it deliberately does not intercept requests.
    # On activation it clears caches created by older Courier Control workers,
    # then immediately takes control so stale navigation/cache behaviour disappears.
    script="""self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.map(key=>caches.delete(key)))).then(()=>self.clients.claim())));"""
    response=HttpResponse(script,content_type='application/javascript')
    response['Service-Worker-Allowed']='/'
    response['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    return response
