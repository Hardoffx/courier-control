from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    Run = apps.get_model('deliveries', 'RouteRun')
    Assignment = apps.get_model('deliveries', 'CourierAssignment')
    Audit = apps.get_model('deliveries', 'CourierScheduleAudit')
    User = apps.get_model('accounts', 'User')
    alias = schema_editor.connection.alias
    today = timezone.localdate()
    User.objects.using(alias).filter(role='courier', is_active=False, tracking_end_date__isnull=True).update(tracking_end_date=today)
    for run in Run.objects.using(alias).exclude(assigned_courier_id=None).select_related('route').iterator():
        Assignment.objects.using(alias).get_or_create(courier_id=run.assigned_courier_id, date=run.run_date, source_run_id=run.pk,
            defaults={'run_id': run.pk, 'route_name': run.route.name, 'frozen': run.run_date < today})
    # A surviving assignment proves only this date. It does not prove continuity,
    # earlier assignees, or that every missing historical day was a day off.
    for courier_id in Run.objects.using(alias).exclude(assigned_courier_id=None).values_list('assigned_courier_id', flat=True).distinct():
        Audit.objects.using(alias).create(courier_id=courier_id, action='legacy_snapshot',
            details={'date': str(today), 'source': 'surviving RouteRun assignments; prior changes unknown'})


class Migration(migrations.Migration):
    dependencies = [('deliveries', '0009_courierassignment_courierdayoff_courierscheduleaudit'),
                    ('accounts', '0003_user_schedule_revision_user_tracking_end_date_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
