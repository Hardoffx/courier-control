from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_archivable_courier'),
        ('deliveries', '0010_backfill_assignment_evidence'),
    ]
    operations = [
        migrations.AddField(model_name='route', name='archived_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='route', name='archived_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='route', name='archive_reason', field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name='route', name='archived_was_active', field=models.BooleanField(default=False)),
        migrations.CreateModel(
            name='ArchiveEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('route', 'Маршрут'), ('courier', 'Курьер')], max_length=12)),
                ('object_id', models.PositiveBigIntegerField()),
                ('object_label', models.CharField(max_length=255)),
                ('action', models.CharField(choices=[('archive', 'В архив'), ('restore', 'Восстановлен')], max_length=12)),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-id',)},
        ),
        migrations.AddIndex(model_name='archiveevent', index=models.Index(fields=['kind', 'object_id'], name='archive_event_object_idx')),
    ]
