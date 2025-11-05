"""
Tests for AI Implementation

To run tests:
    python manage.py test ai_implementation
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import TravelSearch, ConsolidatedResult
from datetime import date, timedelta


class AIImplementationTestCase(TestCase):
    """Test cases for AI implementation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_search_home_requires_login(self):
        """Test that search home page requires authentication"""
        response = self.client.get('/ai/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_search_home_with_login(self):
        """Test that authenticated users can access search home"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/ai/')
        self.assertEqual(response.status_code, 200)
    
    def test_create_travel_search(self):
        """Test creating a travel search"""
        search = TravelSearch.objects.create(
            user=self.user,
            destination='Paris',
            origin='New York',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            adults=2,
            rooms=1
        )
        self.assertEqual(search.destination, 'Paris')
        self.assertEqual(search.adults, 2)
        self.assertFalse(search.is_completed)
    
    def test_travel_search_model_str(self):
        """Test string representation of TravelSearch"""
        search = TravelSearch.objects.create(
            user=self.user,
            destination='Tokyo',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=40),
            adults=1
        )
        expected = f"Search: Tokyo ({search.start_date} to {search.end_date})"
        self.assertEqual(str(search), expected)


