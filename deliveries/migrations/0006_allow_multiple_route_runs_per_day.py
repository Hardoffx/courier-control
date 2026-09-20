from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('deliveries', '0005_delivery_courier_daily_note'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='routerun',
            name='unique_route_run_per_day',
        ),
        migrations.AlterModelOptions(
            name='routerun',
            options={'ordering': ('-run_date', '-created_at', 'route__name')},
        ),
    ]
