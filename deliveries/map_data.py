def delivery_map_item(delivery):
    point = delivery.point
    if not point or point.latitude is None or point.longitude is None:
        return None
    return {
        'id': delivery.pk,
        'order': delivery.route_order,
        'label': delivery.source_label or point.name or point.code or 'Точка',
        'address': delivery.address,
        'time_window': delivery.time_window,
        'status': delivery.status,
        # Yandex JS API uses [longitude, latitude].
        'coordinates': [float(point.longitude), float(point.latitude)],
    }


def delivery_map_items(deliveries):
    items = []
    for delivery in deliveries:
        item = delivery_map_item(delivery)
        if item:
            items.append(item)
    return items
