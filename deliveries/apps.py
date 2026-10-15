from django.apps import AppConfig


class DeliveriesConfig(AppConfig):
    name = 'deliveries'

    def ready(self):
        from . import schedule_signals  # noqa: F401
