import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase
from .import_staging import consume_upload, stage_upload


class ImportStagingConfigTests(SimpleTestCase):
    def test_environment_directory_is_used_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'private-stage'
            with patch.dict(os.environ,{'IMPORT_STAGING_DIR':str(root)}):
                token=stage_upload(b'test-xlsx-bytes',17,'route.xlsx')
                files=list(root.glob('*.xlsx'))
                self.assertEqual(len(files),1)
                if os.name=='posix':
                    self.assertEqual(root.stat().st_mode & 0o777,0o700)
                    self.assertEqual(files[0].stat().st_mode & 0o777,0o600)
                name,content=consume_upload(token,17)
                self.assertEqual(name,'route.xlsx'); self.assertEqual(content,b'test-xlsx-bytes')
                self.assertFalse(list(root.glob('*.xlsx')))
