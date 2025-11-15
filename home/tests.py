from django.test import TestCase, Client
from django.urls import reverse


class HomeViewTest(TestCase):
    """Test cases for home view"""

    def setUp(self):
        self.client = Client()

    def test_home_view_accessible(self):
        """Test that home view is accessible"""
        response = self.client.get(reverse('home:index'))
        self.assertEqual(response.status_code, 200)

    def test_home_view_uses_correct_template(self):
        """Test that home view uses correct template"""
        response = self.client.get(reverse('home:index'))
        self.assertTemplateUsed(response, 'index.html')

    def test_home_view_accessible_without_login(self):
        """Test that home view is accessible without authentication"""
        response = self.client.get(reverse('home:index'))
        self.assertEqual(response.status_code, 200)

    def test_home_view_get_request(self):
        """Test GET request to home view"""
        response = self.client.get(reverse('home:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.content)
