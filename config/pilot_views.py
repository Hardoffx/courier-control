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

@never_cache
def service_worker(request):
    script="""const STATIC_CACHE='courier-static-v1';const OLD_PREFIXES=['courier-shell-','courier-control-'];self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==STATIC_CACHE&&OLD_PREFIXES.some(prefix=>key.startsWith(prefix))).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));self.addEventListener('fetch',event=>{const request=event.request;if(request.method!=='GET')return;const url=new URL(request.url);if(url.origin!==self.location.origin||!url.pathname.startsWith('/static/'))return;event.respondWith(caches.open(STATIC_CACHE).then(async cache=>{const cached=await cache.match(request);if(cached)return cached;const response=await fetch(request);if(response.ok)cache.put(request,response.clone());return response}))});"""
    response=HttpResponse(script,content_type='application/javascript'); response['Service-Worker-Allowed']='/'
    return response
