from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('deliveries', '0004_route_order_learning')]
    operations = [
        migrations.AddField(
            model_name='delivery',
            name='courier_daily_note',
            field=models.CharField(blank=True, help_text='Одноразовая заметка курьера только для этой доставки этого дня', max_length=500),
        ),
    ]
