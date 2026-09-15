from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('accounts','0001_initial')]
    operations = [
        migrations.AddField(
            model_name='user',
            name='is_reserve_courier',
            field=models.BooleanField(default=False, help_text='Резервный курьер без постоянного маршрута; может быть назначен на любой RouteRun'),
        ),
    ]
