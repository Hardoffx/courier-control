from django.core.management.base import BaseCommand
from deliveries.geocoding import geocode_pending_points


class Command(BaseCommand):
    help = 'Geocode permanent delivery points through Yandex Geocoder API.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)
        parser.add_argument('--force', action='store_true', help='Re-geocode points that already have coordinates.')

    def handle(self, *args, **options):
        stats = geocode_pending_points(limit=options['limit'], force=options['force'])
        if stats['skipped_no_key']:
            self.stdout.write(self.style.WARNING('YANDEX_GEOCODER_API_KEY is not configured; nothing changed.'))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Checked {stats['checked']}; geocoded {stats['ok']}; failed {stats['failed']}"
        ))
