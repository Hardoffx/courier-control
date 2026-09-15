import os
import secrets
import time
from pathlib import Path
from django.conf import settings
from django.core import signing

MAX_AGE_SECONDS=30*60
TOKEN_SALT='courier-control.import-stage.v1'

def _root():
    configured=os.getenv('IMPORT_STAGING_DIR') or getattr(settings,'IMPORT_STAGING_DIR',None)
    root=Path(configured) if configured else Path(settings.BASE_DIR)/'var'/'import-staging'
    root.mkdir(parents=True,exist_ok=True)
    try: root.chmod(0o700)
    except OSError: pass
    return root

def cleanup_staged(now=None):
    now=now or time.time(); removed=0
    for path in _root().glob('*.xlsx'):
        try:
            if now-path.stat().st_mtime>MAX_AGE_SECONDS: path.unlink(); removed+=1
        except FileNotFoundError: pass
    return removed

def stage_upload(content,user_id,filename):
    cleanup_staged(); key=secrets.token_urlsafe(24); path=_root()/f'{key}.xlsx'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,'wb') as handle: handle.write(content)
    except Exception:
        path.unlink(missing_ok=True); raise
    return signing.dumps({'key':key,'uid':int(user_id),'name':Path(filename).name[:180]},salt=TOKEN_SALT,compress=True)

def consume_upload(token,user_id):
    try: data=signing.loads(token,salt=TOKEN_SALT,max_age=MAX_AGE_SECONDS)
    except signing.BadSignature as exc: raise ValueError('Предпросмотр истёк или недействителен. Загрузите файл ещё раз.') from exc
    if int(data.get('uid',-1))!=int(user_id): raise ValueError('Этот предпросмотр принадлежит другому пользователю.')
    key=str(data.get('key',''))
    if not key or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in key): raise ValueError('Недействительный токен импорта.')
    path=_root()/f'{key}.xlsx'
    try: content=path.read_bytes()
    except FileNotFoundError as exc: raise ValueError('Файл предпросмотра уже использован или истёк.') from exc
    path.unlink(missing_ok=True)
    return data.get('name') or 'route.xlsx',content
