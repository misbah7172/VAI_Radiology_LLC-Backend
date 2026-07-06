from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import User


class UserModelTests(TestCase):
    """Tests for the custom User model."""

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='test')

    def test_email_is_normalized(self):
        user = User.objects.create_user(
            email='test@EXAMPLE.COM',
            password='testpass123'
        )
        self.assertEqual(user.email, 'test@example.com')


class AuthAPITests(TestCase):
    """Tests for authentication endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='demo@vai.com',
            password='demo1234',
            full_name='Demo User'
        )

    def test_login_success(self):
        response = self.client.post(reverse('auth-login'), {
            'email': 'demo@vai.com',
            'password': 'demo1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('auth-login'), {
            'email': 'demo@vai.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 400)

    def test_me_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['email'], 'demo@vai.com')

    def test_me_unauthenticated(self):
        response = self.client.get(reverse('auth-me'))
        self.assertEqual(response.status_code, 401)
