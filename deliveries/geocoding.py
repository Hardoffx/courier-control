import json
import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.utils import timezone

from .models import DeliveryPoint

logger = logging.getLogger(__name__)
GEOCODER_URL = 'https://geocode-maps.yandex.ru/1.x/'


def geocode_point(point, *, force=False, opener=urlopen):
    """Resolve a permanent point through Yandex Geocoder.

    Safe to call without a configured key: the point remains pending and no
    external request is attempted. Existing successful coordinates are kept
    unless force=True.
    """
    if point.geocode_status == DeliveryPoint.GeocodeStatus.OK and point.latitude is not None and point.longitude is not None and not force:
        return True
    key = getattr(settings, 'YANDEX_GEOCODER_API_KEY', '')
    if not key:
        return False
    address = (point.address or '').strip()
    if not address:
        _mark_failed(point)
        return False
    params = urlencode({'apikey': key, 'geocode': address, 'format': 'json', 'results': 1, 'lang': 'ru_RU'})
    request = Request(f'{GEOCODER_URL}?{params}', headers={'User-Agent': 'Courier-Control/1.0'})
    try:
        with opener(request, timeout=8) as response:
            payload = json.loads(response.read().decode('utf-8'))
        members = payload['response']['GeoObjectCollection']['featureMember']
        if not members:
            _mark_failed(point)
            return False
        obj = members[0]['GeoObject']
        lon_raw, lat_raw = obj['Point']['pos'].split()
        longitude, latitude = Decimal(lon_raw), Decimal(lat_raw)
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError('Yandex returned coordinates outside valid range')
        metadata = obj.get('metaDataProperty', {}).get('GeocoderMetaData', {})
        normalized = (metadata.get('text') or address)[:500]
        point.longitude = longitude
        point.latitude = latitude
        point.geocode_status = DeliveryPoint.GeocodeStatus.OK
        point.geocoded_address = normalized
        point.geocoded_at = timezone.now()
        point.save(update_fields=['longitude','latitude','geocode_status','geocoded_address','geocoded_at','updated_at'])
        return True
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        logger.warning('Yandex geocoding failed for point %s: %s', point.pk, exc)
        _mark_failed(point)
        return False


def _mark_failed(point):
    point.geocode_status = DeliveryPoint.GeocodeStatus.FAILED
    point.geocoded_at = timezone.now()
    point.save(update_fields=['geocode_status','geocoded_at','updated_at'])


def geocode_pending_points(*, limit=100, force=False):
    qs = DeliveryPoint.objects.filter(is_active=True).order_by('id')
    if not force:
        qs = qs.exclude(geocode_status=DeliveryPoint.GeocodeStatus.OK, latitude__isnull=False, longitude__isnull=False)
    stats = {'checked': 0, 'ok': 0, 'failed': 0, 'skipped_no_key': False}
    if not getattr(settings, 'YANDEX_GEOCODER_API_KEY', ''):
        stats['skipped_no_key'] = True
        return stats
    for point in qs[:max(1, min(int(limit), 1000))]:
        stats['checked'] += 1
        if geocode_point(point, force=force): stats['ok'] += 1
        else: stats['failed'] += 1
    return stats
