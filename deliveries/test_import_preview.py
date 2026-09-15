from io import BytesIO
from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook
from .import_services import preview_workbook
from .models import Delivery, DeliveryPoint


class ImportPreviewContractTests(TestCase):
    def workbook(self,rows):
        wb=Workbook(); ws=wb.active; ws.append(['Код','Адрес','Время','№'])
        for row in rows: ws.append(row)
        stream=BytesIO(); wb.save(stream); return stream.getvalue()

    def test_preview_reports_new_point_without_writing(self):
        content=self.workbook([['999','Москва, Новая 1','10:00',1]])
        summary=preview_workbook(content)
        self.assertEqual(summary.total_rows,1); self.assertEqual(summary.new_points,1); self.assertEqual(summary.matched,0)
        self.assertEqual(DeliveryPoint.objects.count(),0); self.assertEqual(Delivery.objects.count(),0)
        row=summary.preview[0]
        self.assertEqual(row['row'],2); self.assertEqual(row['label'],'999'); self.assertEqual(row['address'],'Москва, Новая 1'); self.assertTrue(row['new_point']); self.assertFalse(row['duplicate'])

    def test_preview_uses_canonical_point_data_and_match_label(self):
        point=DeliveryPoint.objects.create(name='CMD 458',code='458',address='Москва, Каноническая 10',phone='+79990000000',kind=DeliveryPoint.Kind.CMD)
        summary=preview_workbook(self.workbook([['458','Старый адрес','09:30',1]]))
        self.assertEqual(summary.matched,1); self.assertEqual(summary.new_points,0)
        row=summary.preview[0]
        self.assertEqual(row['address'],point.address); self.assertEqual(row['match'],str(point)); self.assertFalse(row['new_point'])

    def test_preview_marks_existing_and_in_file_duplicates(self):
        day=timezone.localdate()
        Delivery.objects.create(delivery_date=day,address='Москва, A',source_label='111',route_order=1)
        content=self.workbook([['111','Москва, A','09:00',1],['222','Москва, B','10:00',2],['222','Москва, B','10:00',2]])
        summary=preview_workbook(content)
        self.assertEqual(summary.skipped,2)
        self.assertTrue(summary.preview[0]['duplicate']); self.assertFalse(summary.preview[1]['duplicate']); self.assertTrue(summary.preview[2]['duplicate'])
        self.assertEqual(summary.new_points,2)
