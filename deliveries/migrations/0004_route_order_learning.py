from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0003_deliverypoint_geocoding'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CourierRouteOrderPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point_order', models.JSONField(blank=True, default=list, help_text='Приоритетный порядок точек для этого курьера в этом варианте маршрута')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('courier', models.ForeignKey(limit_choices_to={'role': 'courier'}, on_delete=django.db.models.deletion.CASCADE, related_name='route_order_preferences', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='courier_order_preferences', to='deliveries.routetemplate')),
            ],
            options={'ordering': ('template__route__name', 'courier__username')},
        ),
        migrations.CreateModel(
            name='RouteOrderSuggestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_point_order', models.JSONField(blank=True, default=list)),
                ('proposed_point_order', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('pending', 'Ожидает решения'), ('applied_template', 'Принят для маршрута'), ('applied_courier', 'Сохранён для курьера'), ('dismissed', 'Только на этот день')], default='pending', max_length=24)),
                ('decided_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('courier', models.ForeignKey(blank=True, limit_choices_to={'role': 'courier'}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='route_order_suggestions', to=settings.AUTH_USER_MODEL)),
                ('decided_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='route_order_decisions', to=settings.AUTH_USER_MODEL)),
                ('run', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='order_suggestion', to='deliveries.routerun')),
            ],
            options={'ordering': ('-updated_at',)},
        ),
        migrations.AddConstraint(
            model_name='courierrouteorderpreference',
            constraint=models.UniqueConstraint(fields=('template', 'courier'), name='unique_courier_order_per_template'),
        ),
    ]
