from django.db import migrations, models


def split_weekend_templates(apps, schema_editor):
    RouteTemplate = apps.get_model('deliveries', 'RouteTemplate')
    RouteTemplateItem = apps.get_model('deliveries', 'RouteTemplateItem')

    for legacy in list(RouteTemplate.objects.filter(kind='weekend').order_by('id')):
        route_id = legacy.route_id
        name = legacy.name
        legacy.kind = 'saturday'
        legacy.save(update_fields=['kind'])

        sunday, created = RouteTemplate.objects.get_or_create(
            route_id=route_id,
            kind='sunday',
            name=name,
            defaults={'is_active': legacy.is_active},
        )
        if not created:
            continue

        items = RouteTemplateItem.objects.filter(template=legacy).order_by('route_order', 'id')
        RouteTemplateItem.objects.bulk_create([
            RouteTemplateItem(
                template=sunday,
                point_id=item.point_id,
                route_order=item.route_order,
                enabled_by_default=item.enabled_by_default,
                time_window=item.time_window,
                comment=item.comment,
            )
            for item in items
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('deliveries', '0007_allow_blank_point_codes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='routetemplate',
            name='kind',
            field=models.CharField(
                choices=[
                    ('weekday', 'Будни'),
                    ('saturday', 'Суббота'),
                    ('sunday', 'Воскресенье'),
                    ('weekend', 'Выходные'),
                    ('custom', 'Особый'),
                ],
                max_length=20,
            ),
        ),
        migrations.RunPython(split_weekend_templates, migrations.RunPython.noop),
    ]
