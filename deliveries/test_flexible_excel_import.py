from io import BytesIO

from django.test import TestCase
from openpyxl import Workbook

from .import_services import _rows, normalize_delivery_address
from .models import Delivery, DeliveryPoint


class FlexibleExcelImportTests(TestCase):
    def workbook(self, rows, header=None):
        wb = Workbook()
        ws = wb.active
        if header:
            ws.append(header)
        for row in rows:
            ws.append(row)
        stream = BytesIO()
        wb.save(stream)
        return stream.getvalue()

    def test_headerless_workbook_detects_columns_and_preserves_order(self):
        content = self.workbook([
            ['МО Митино-1', 'Москва г, пер 3-й Митинский, д. 7', '', '12:30-16:00'],
            ['2939', 'Москва г, Митинская ул, дом № 44', '', '16:00-18:00'],
            ['КК: В+АПМИТИНО', 'Москва г, ш. Пятницкое, д. 15, к. 3', 'БМ', '14:00-18:00'],
        ])

        rows = _rows(content, create_points=False)

        self.assertEqual([row['source_label'] for row in rows], [
            'МО Митино-1',
            '2939',
            'КК: В+АПМИТИНО',
        ])
        self.assertEqual([row['route_order'] for row in rows], [1, 2, 3])
        self.assertEqual([row['time_window'] for row in rows], [
            '12:30-16:00',
            '16:00-18:00',
            '14:00-18:00',
        ])
        self.assertEqual(rows[0]['address'], 'Москва, пер 3-й Митинский 7')
        self.assertEqual(rows[2]['address'], 'Москва, ш Пятницкое 15к3')

    def test_columns_are_detected_by_content_not_fixed_position(self):
        content = self.workbook([
            ['10:00-12:00', 'Москва г, Тестовая ул, дом № 5, корпус 2', '458'],
            ['12:00-14:00', 'Москва г, Другая ул, д. 8', 'МО Тест'],
        ])

        rows = _rows(content, create_points=False)

        self.assertEqual(rows[0]['source_label'], '458')
        self.assertEqual(rows[0]['address'], 'Москва, ул Тестовая 5к2')
        self.assertEqual(rows[0]['time_window'], '10:00-12:00')
        self.assertEqual(rows[1]['source_label'], 'МО Тест')

    def test_address_normalization_keeps_building_and_removes_interior_details(self):
        self.assertEqual(
            normalize_delivery_address(
                'Москва г, Митинский 3-й пер, дом № 4, корпус 1, '
                'помещение VII, этаж 2, комната 14'
            ),
            'Москва, пер Митинский 3-й 4к1',
        )
        self.assertEqual(
            normalize_delivery_address(
                'Москва г, ул Вишнёвая, д. 13, к. 1, стр. 1, офис 205'
            ),
            'Москва, ул Вишнёвая 13к1с1',
        )

    def test_existing_headered_workbook_still_works(self):
        content = self.workbook(
            [['458', 'Москва г, Тестовая ул, дом № 10', '09:00-11:00']],
            header=['Код', 'Адрес', 'Время'],
        )

        rows = _rows(content, create_points=False)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['source_label'], '458')
        self.assertEqual(rows[0]['address'], 'Москва, ул Тестовая 10')

    def test_current_laboratory_profile_classification(self):
        self.assertEqual(Delivery.infer_point_kind('458'), DeliveryPoint.Kind.CMD)
        self.assertEqual(
            Delivery.infer_point_kind('5827/5958/6113'),
            DeliveryPoint.Kind.CMD,
        )
        self.assertEqual(
            Delivery.infer_point_kind('МО Митино-1'),
            DeliveryPoint.Kind.INVITRO,
        )
        self.assertEqual(
            Delivery.infer_point_kind('КК: В+АПМИТИНО'),
            DeliveryPoint.Kind.INVITRO,
        )
