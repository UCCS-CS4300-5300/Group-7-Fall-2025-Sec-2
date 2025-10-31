from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from .models import UserProfile, Itinerary
from .forms import SignUpForm, ItineraryForm
import json


class UserProfileModelTest(TestCase):
    """Test cases for UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_user_profile(self):
        """Test creating a user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.phone_number, '+1234567890')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
    
    def test_user_profile_str_method(self):
        """Test string representation of user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )
        expected_str = f"{self.user.username} - +1234567890"
        self.assertEqual(str(profile), expected_str)
    
    def test_valid_phone_numbers(self):
        """Test valid phone number formats"""
        valid_numbers = [
            '+1234567890',
            '1234567890',
            '123456789',
        ]
        for number in valid_numbers:
            profile = UserProfile(user=self.user, phone_number=number)
            try:
                profile.full_clean()
            except ValidationError:
                self.fail(f"Phone number {number} should be valid but raised ValidationError")
    
    def test_invalid_phone_numbers(self):
        """Test invalid phone number formats"""
        invalid_numbers = [
            '12345',  # Too short
            '+12345678901234567',  # Too long
            'abcd1234567',  # Contains letters
        ]
        for number in invalid_numbers:
            profile = UserProfile(user=self.user, phone_number=number)
            with self.assertRaises(ValidationError):
                profile.full_clean()
    
    def test_one_to_one_relationship(self):
        """Test that one user can only have one profile"""
        UserProfile.objects.create(user=self.user, phone_number='+1234567890')
        # Attempting to create another profile for same user should fail
        with self.assertRaises(Exception):
            UserProfile.objects.create(user=self.user, phone_number='+9876543210')


class ItineraryModelTest(TestCase):
    """Test cases for Itinerary model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.start_date = date.today()
        self.end_date = self.start_date + timedelta(days=7)
    
    def test_create_itinerary(self):
        """Test creating an itinerary"""
        itinerary = Itinerary.objects.create(
            user=self.user,
            title='Summer Vacation',
            description='Beach trip',
            destination='Hawaii',
            start_date=self.start_date,
            end_date=self.end_date
        )
        self.assertEqual(itinerary.user, self.user)
        self.assertEqual(itinerary.title, 'Summer Vacation')
        self.assertEqual(itinerary.destination, 'Hawaii')
        self.assertTrue(itinerary.is_active)
    
    def test_itinerary_str_method(self):
        """Test string representation of itinerary"""
        itinerary = Itinerary.objects.create(
            user=self.user,
            title='Summer Vacation',
            destination='Hawaii',
            start_date=self.start_date,
            end_date=self.end_date
        )
        expected_str = "Summer Vacation - Hawaii"
        self.assertEqual(str(itinerary), expected_str)
    
    def test_itinerary_ordering(self):
        """Test that itineraries are ordered by creation date (newest first)"""
        itinerary1 = Itinerary.objects.create(
            user=self.user,
            title='Trip 1',
            destination='Dest 1',
            start_date=self.start_date,
            end_date=self.end_date
        )
        itinerary2 = Itinerary.objects.create(
            user=self.user,
            title='Trip 2',
            destination='Dest 2',
            start_date=self.start_date,
            end_date=self.end_date
        )
        itineraries = Itinerary.objects.all()
        self.assertEqual(itineraries[0], itinerary2)
        self.assertEqual(itineraries[1], itinerary1)
    
    def test_itinerary_optional_description(self):
        """Test that description is optional"""
        itinerary = Itinerary.objects.create(
            user=self.user,
            title='Quick Trip',
            destination='City',
            start_date=self.start_date,
            end_date=self.end_date
        )
        self.assertIsNone(itinerary.description)


class SignUpFormTest(TestCase):
    """Test cases for SignUpForm"""
    
    def test_valid_signup_form(self):
        """Test valid signup form data"""
        form_data = {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        }
        form = SignUpForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_missing_required_fields(self):
        """Test form with missing required fields"""
        form_data = {
            'username': 'newuser',
            'email': 'john@example.com',
        }
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)
        self.assertIn('phone_number', form.errors)
    
    def test_password_mismatch(self):
        """Test form with mismatched passwords"""
        form_data = {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'DifferentPass123!'
        }
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_invalid_email(self):
        """Test form with invalid email"""
        form_data = {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        }
        form = SignUpForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class ItineraryFormTest(TestCase):
    """Test cases for ItineraryForm"""
    
    def setUp(self):
        self.start_date = date.today()
        self.end_date = self.start_date + timedelta(days=7)
    
    def test_valid_itinerary_form(self):
        """Test valid itinerary form data"""
        form_data = {
            'title': 'Summer Vacation',
            'description': 'Beach trip',
            'destination': 'Hawaii',
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        form = ItineraryForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_missing_required_fields(self):
        """Test form with missing required fields"""
        form_data = {
            'title': 'Summer Vacation',
        }
        form = ItineraryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('destination', form.errors)
        self.assertIn('start_date', form.errors)
        self.assertIn('end_date', form.errors)
    
    def test_optional_description(self):
        """Test that description is optional"""
        form_data = {
            'title': 'Quick Trip',
            'destination': 'City',
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        form = ItineraryForm(data=form_data)
        self.assertTrue(form.is_valid())


class HomeViewTest(TestCase):
    """Test cases for home view"""
    
    def test_home_view_accessible(self):
        """Test that home view is accessible"""
        client = Client()
        response = client.get(reverse('accounts:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/home.html')


class LoginViewTest(TestCase):
    """Test cases for login view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_view_get(self):
        """Test GET request to login view"""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
    
    def test_login_with_valid_credentials(self):
        """Test login with valid email and password"""
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))
    
    def test_login_with_invalid_email(self):
        """Test login with invalid email"""
        response = self.client.post(reverse('accounts:login'), {
            'email': 'wrong@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')
    
    def test_login_with_invalid_password(self):
        """Test login with invalid password"""
        response = self.client.post(reverse('accounts:login'), {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated users are redirected from login page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('accounts:dashboard'))


class SignupViewTest(TestCase):
    """Test cases for signup view"""
    
    def setUp(self):
        self.client = Client()
    
    def test_signup_view_get(self):
        """Test GET request to signup view"""
        response = self.client.get(reverse('accounts:signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')
    
    def test_signup_with_valid_data(self):
        """Test signup with valid data"""
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(UserProfile.objects.filter(user__username='newuser').exists())
    
    def test_signup_creates_user_profile(self):
        """Test that signup creates user profile"""
        self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        })
        user = User.objects.get(username='newuser')
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.phone_number, '+1234567890')
    
    def test_signup_auto_login(self):
        """Test that user is automatically logged in after signup"""
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        }, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated users are redirected from signup page"""
        User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:signup'))
        self.assertRedirects(response, reverse('accounts:dashboard'))


class DashboardViewTest(TestCase):
    """Test cases for dashboard view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number='+1234567890'
        )
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/dashboard.html')
        self.assertEqual(response.context['user_profile'], self.profile)
    
    def test_dashboard_creates_missing_profile(self):
        """Test that dashboard creates user profile if it doesn't exist"""
        # Create user without profile
        user2 = User.objects.create_user(username='user2', password='pass123')
        self.client.login(username='user2', password='pass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(user=user2).exists())
    
    def test_dashboard_shows_itineraries(self):
        """Test that dashboard displays user's itineraries"""
        self.client.login(username='testuser', password='testpass123')
        Itinerary.objects.create(
            user=self.user,
            title='Trip 1',
            destination='Dest 1',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            is_active=True
        )
        Itinerary.objects.create(
            user=self.user,
            title='Trip 2',
            destination='Dest 2',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            is_active=False
        )
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(len(response.context['active_trips']), 1)
        self.assertEqual(len(response.context['saved_itineraries']), 1)


class LogoutViewTest(TestCase):
    """Test cases for logout view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_logout_redirects_to_home(self):
        """Test that logout redirects to home page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:home'))
    
    def test_user_logged_out(self):
        """Test that user is actually logged out"""
        self.client.login(username='testuser', password='testpass123')
        self.client.get(reverse('accounts:logout'))
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 302)  # Should redirect to login


class CreateItineraryViewTest(TestCase):
    """Test cases for create itinerary view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.start_date = date.today()
        self.end_date = self.start_date + timedelta(days=7)
    
    def test_create_itinerary_requires_login(self):
        """Test that creating itinerary requires authentication"""
        response = self.client.post(reverse('accounts:create_itinerary'), {
            'title': 'Test Trip',
            'destination': 'Test Dest',
            'start_date': self.start_date,
            'end_date': self.end_date
        })
        self.assertEqual(response.status_code, 302)
    
    def test_create_itinerary_requires_post(self):
        """Test that create itinerary only accepts POST"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:create_itinerary'))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_create_itinerary_success(self):
        """Test successful itinerary creation"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:create_itinerary'), {
            'title': 'Test Trip',
            'description': 'Test Description',
            'destination': 'Test Dest',
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('itinerary_id', data)
        self.assertTrue(Itinerary.objects.filter(user=self.user, title='Test Trip').exists())
    
    def test_create_itinerary_invalid_data(self):
        """Test itinerary creation with invalid data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:create_itinerary'), {
            'title': 'Test Trip',
            # Missing required fields
        })
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)


class GetItinerariesViewTest(TestCase):
    """Test cases for get itineraries view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.start_date = date.today()
        self.end_date = self.start_date + timedelta(days=7)
    
    def test_get_itineraries_requires_login(self):
        """Test that getting itineraries requires authentication"""
        response = self.client.get(reverse('accounts:get_itineraries'))
        self.assertEqual(response.status_code, 302)
    
    def test_get_itineraries_returns_json(self):
        """Test that get itineraries returns JSON"""
        self.client.login(username='testuser', password='testpass123')
        Itinerary.objects.create(
            user=self.user,
            title='Trip 1',
            destination='Dest 1',
            start_date=self.start_date,
            end_date=self.end_date
        )
        response = self.client.get(reverse('accounts:get_itineraries'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('itineraries', data)
        self.assertEqual(len(data['itineraries']), 1)
        self.assertEqual(data['itineraries'][0]['title'], 'Trip 1')
    
    def test_get_itineraries_only_user_itineraries(self):
        """Test that get itineraries only returns current user's itineraries"""
        other_user = User.objects.create_user(username='other', password='pass123')
        Itinerary.objects.create(
            user=other_user,
            title='Other Trip',
            destination='Other Dest',
            start_date=self.start_date,
            end_date=self.end_date
        )
        Itinerary.objects.create(
            user=self.user,
            title='My Trip',
            destination='My Dest',
            start_date=self.start_date,
            end_date=self.end_date
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:get_itineraries'))
        data = json.loads(response.content)
        self.assertEqual(len(data['itineraries']), 1)
        self.assertEqual(data['itineraries'][0]['title'], 'My Trip')

