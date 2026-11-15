import io
import gzip
import json
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from accounts.models import User
from core.models import CompanySetting


class DatabaseBackupRestoreTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpassword123',
            roles=['ADMIN']
        )
        self.client.force_login(self.admin_user)

        self.company_setting = CompanySetting.get_settings()
        self.company_setting.company_name = 'Gadget Store Test'
        self.company_setting.is_customized = True
        self.company_setting.save()

    def test_create_backup_download(self):
        url = reverse('core:create_backup') + '?download=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/gzip')
        self.assertTrue('attachment; filename=' in response['Content-Disposition'])

        # Verify decompressed content is valid JSON
        decompressed = gzip.decompress(response.content)
        parsed = json.loads(decompressed.decode('utf-8'))
        self.assertIsInstance(parsed, list)

        # Verify a local file was saved in BASE_DIR / 'backups'
        backup_dir = settings.BASE_DIR / 'backups'
        self.assertTrue(backup_dir.exists())

    def test_ajax_list_local_backups(self):
        # Create a backup first so there is at least one file
        self.client.get(reverse('core:create_backup') + '?download=1')

        url = reverse('core:ajax_list_local_backups')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIsInstance(data['backups'], list)
        self.assertGreaterEqual(len(data['backups']), 1)
        self.assertIn('filename', data['backups'][0])
        self.assertIn('size_kb', data['backups'][0])
        self.assertIn('modified', data['backups'][0])

    def test_db_backup_restore_from_server_file(self):
        # Create a backup first
        self.client.get(reverse('core:create_backup') + '?download=1')

        # List to get the filename
        list_res = self.client.get(reverse('core:ajax_list_local_backups')).json()
        latest_file = list_res['backups'][0]['filename']

        # Call restore using local_backup_filename
        restore_url = reverse('core:backup_restore')
        response = self.client.post(restore_url, {
            'local_backup_filename': latest_file,
            'restore_mode': 'merge'
        })
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        self.assertTrue(res_data.get('reload'))
