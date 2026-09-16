from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_local_env(path):
    """Load the deployment .env for direct manage.py commands.

    systemd already supplies the same file to Gunicorn. Loading it here keeps
    migrations/collectstatic/createsuperuser on the exact same database and
    settings when they are run directly from the checkout. Existing process
    environment values always win.
    """
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, value = line.split('=', 1)
        key = key.strip()
        if not key or not key.replace('_', 'a').isalnum() or key[0].isdigit():
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_local_env(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]
DOMAIN_SPLIT_ENABLED = os.getenv('DOMAIN_SPLIT_ENABLED', '0') == '1'
COURIER_HOST = os.getenv('COURIER_HOST', 'courier.routecontrol.ru').strip().lower()
CONTROL_HOST = os.getenv('CONTROL_HOST', 'control.routecontrol.ru').strip().lower()
YANDEX_MAPS_JS_API_KEY = os.getenv('YANDEX_MAPS_JS_API_KEY', '').strip()
YANDEX_GEOCODER_API_KEY = os.getenv('YANDEX_GEOCODER_API_KEY', '').strip()
YANDEX_MAPS_LANG = os.getenv('YANDEX_MAPS_LANG', 'ru_RU').strip() or 'ru_RU'

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'accounts', 'deliveries',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config.middleware.PortalHostMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':Path(os.getenv('SQLITE_PATH', str(BASE_DIR/'db.sqlite3'))),'OPTIONS':{'timeout':20}}}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

if not DEBUG:
    if SECRET_KEY == 'dev-only-change-me': raise RuntimeError('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=0')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'INFO')
LOGGING = {'version':1,'disable_existing_loggers':False,'formatters':{'standard':{'format':'%(asctime)s %(levelname)s %(name)s %(message)s'}},'handlers':{'console':{'class':'logging.StreamHandler','formatter':'standard'}},'root':{'handlers':['console'],'level':LOG_LEVEL},'loggers':{'django.request':{'handlers':['console'],'level':'WARNING','propagate':False}}}