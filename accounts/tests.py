"""
Tests for Accounts and Email/Username Authentication Backend.
"""

from django.test import TestCase, Client
from django.contrib.auth import authenticate
from accounts.models import User, UserRole
from core.validators import validate_login


class EmailOrUsernameAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe',
            email='John.Doe@example.com',
            password='SecretPassword123!',
            roles=[UserRole.MANAGER]
        )
        self.client = Client()

    def test_authenticate_via_exact_email(self):
        user = authenticate(username='John.Doe@example.com', password='SecretPassword123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'johndoe')

    def test_authenticate_via_lowercase_email(self):
        user = authenticate(username='john.doe@example.com', password='SecretPassword123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'johndoe')

    def test_authenticate_via_uppercase_email(self):
        user = authenticate(username='JOHN.DOE@EXAMPLE.COM', password='SecretPassword123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'johndoe')

    def test_authenticate_via_username(self):
        user = authenticate(username='johndoe', password='SecretPassword123!')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'John.Doe@example.com')

    def test_authenticate_bad_password(self):
        user = authenticate(username='john.doe@example.com', password='WrongPassword')
        self.assertIsNone(user)

    def test_authenticate_nonexistent_user(self):
        user = authenticate(username='nonexistent@example.com', password='SecretPassword123!')
        self.assertIsNone(user)

    def test_authenticate_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        user = authenticate(username='john.doe@example.com', password='SecretPassword123!')
        self.assertIsNotNone(user)
        self.assertFalse(user.is_active)

    def test_validate_login_missing_identifier(self):
        errors = validate_login({'password': 'SecretPassword123!'})
        self.assertIn('email', errors)
        self.assertIn('username', errors)

    def test_validate_login_missing_password(self):
        errors = validate_login({'email': 'john.doe@example.com'})
        self.assertIn('password', errors)

    def test_validate_login_valid_with_email(self):
        errors = validate_login({'email': 'john.doe@example.com', 'password': 'SecretPassword123!'})
        self.assertEqual(errors, {})

    def test_validate_login_valid_with_username(self):
        errors = validate_login({'username': 'johndoe', 'password': 'SecretPassword123!'})
        self.assertEqual(errors, {})

    def test_login_view_ajax_email(self):
        response = self.client.post(
            '/accounts/login/',
            {'email': 'john.doe@example.com', 'password': 'SecretPassword123!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertEqual(data.get('data', {}).get('redirect_url'), '/')

    def test_login_view_ajax_username_fallback(self):
        response = self.client.post(
            '/accounts/login/',
            {'username': 'johndoe', 'password': 'SecretPassword123!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')

    def test_login_view_ajax_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            '/accounts/login/',
            {'email': 'john.doe@example.com', 'password': 'SecretPassword123!'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data.get('status'), 'error')
        self.assertEqual(data.get('title'), 'Account Disabled')

    def test_login_view_ajax_invalid_credentials(self):
        response = self.client.post(
            '/accounts/login/',
            {'email': 'john.doe@example.com', 'password': 'WrongPassword'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data.get('status'), 'error')
