from django.db import migrations, models


def clear_generated_point_codes(apps, schema_editor):
    DeliveryPoint = apps.get_model('deliveries', 'DeliveryPoint')
    DeliveryPoint.objects.filter(code__startswith='point-').update(code='')


class Migration(migrations.Migration):
    dependencies = [('deliveries', '0005_delivery_courier_daily_note')]

    operations = [
        migrations.RemoveConstraint(
            model_name='deliverypoint',
            name='unique_point_code_address',
        ),
        migrations.AddConstraint(
            model_name='deliverypoint',
            constraint=models.UniqueConstraint(
                fields=('code', 'address'),
                condition=~models.Q(code=''),
                name='unique_point_code_address',
            ),
        ),
        migrations.RunPython(clear_generated_point_codes, migrations.RunPython.noop),
    ]
