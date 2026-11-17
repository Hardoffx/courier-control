from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_user_schedule_revision_user_tracking_end_date_and_more')]
    operations = [
        migrations.AddField(model_name='user', name='archived_at', field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name='user', name='archived_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='user', name='archive_reason', field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name='user', name='archived_was_active', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='user', name='archived_previous_tracking_end_date', field=models.DateField(blank=True, null=True)),
    ]
