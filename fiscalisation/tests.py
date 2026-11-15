from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class FiscalisationApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username="fisc_admin", password="password123")
        self.client.login(username="fisc_admin", password="password123")

    def test_dashboard_spa_renders(self):
        resp = self.client.get(reverse('fiscalisation:dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_api_stats(self):
        resp = self.client.get(reverse('fiscalisation:api_stats'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('stats', data)
