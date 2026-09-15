from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache

@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return JsonResponse({'status':'ok','database':'ok'})
    except Exception:
        return JsonResponse({'status':'error','database':'error'}, status=503)

def manifest(request):
    return JsonResponse({
        'name':'Courier Control', 'short_name':'Courier', 'start_url':'/', 'scope':'/',
        'display':'standalone', 'background_color':'#f4f6f8', 'theme_color':'#111827',
        'description':'Маршруты и рабочий экран курьера'
    }, content_type='application/manifest+json')

def service_worker(request):
    script="""const CACHE='courier-shell-v1';self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/login/']))));self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))})"""
    response=HttpResponse(script,content_type='application/javascript'); response['Service-Worker-Allowed']='/'
    return response
