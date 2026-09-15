from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('deliveries', '0002_routes')]

    operations = [
        migrations.AddField(model_name='deliverypoint', name='latitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='deliverypoint', name='longitude', field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name='deliverypoint', name='geocode_status', field=models.CharField(choices=[('pending','Ожидает'),('ok','Найдена'),('failed','Не найдена')], default='pending', max_length=16)),
        migrations.AddField(model_name='deliverypoint', name='geocoded_address', field=models.CharField(blank=True, max_length=500)),
        migrations.AddField(model_name='deliverypoint', name='geocoded_at', field=models.DateTimeField(blank=True, null=True)),
    ]
