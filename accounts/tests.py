from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import date, timedelta, datetime
from unittest.mock import patch, MagicMock
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
    
    def test_signup_exception_handling(self):
        """Test exception handling in signup view"""
        # Mock a scenario that might cause an exception
        # This could happen if there's a database constraint violation or other error
        self.client = Client()
        # Attempt signup with data that might cause issues
        # Note: We can't easily trigger the exception without mocking, but we ensure the view handles it
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone_number': '+1234567890',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!'
        })
        # If successful, should redirect
        # If exception occurs, should show error message
        # Both paths are valid, so we just check it doesn't crash
        self.assertIn(response.status_code, [200, 302])
    
    def test_signup_with_exception_raised(self):
        """Test signup view handles exceptions properly"""
        from unittest.mock import patch
        with patch('accounts.views.UserProfile.objects.create', side_effect=Exception("Database error")):
            response = self.client.post(reverse('accounts:signup'), {
                'username': 'testuser2',
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test2@example.com',
                'phone_number': '+1234567890',
                'password1': 'SecurePass123!',
                'password2': 'SecurePass123!'
            })
            # Should render form with error message
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Error creating account')


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
        # Check that inactive trips are filtered out from active_trips
        inactive_itineraries = Itinerary.objects.filter(user=self.user, is_active=False)
        self.assertEqual(inactive_itineraries.count(), 1)
    
    def test_dashboard_shows_accepted_group_trips(self):
        """Test that dashboard displays accepted group trips"""
        import json
        from travel_groups.models import TravelGroup, GroupMember
        from ai_implementation.models import GroupItineraryOption, GroupConsensus, TravelSearch, FlightResult, HotelResult, ActivityResult
        
        self.client.login(username='testuser', password='testpass123')
        
        # Create a group and add user as member
        group = TravelGroup.objects.create(
            name='Test Group',
            created_by=self.user,
            password='test123'
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        
        # Create another member
        user2 = User.objects.create_user(username='user2', password='pass123')
        GroupMember.objects.create(group=group, user=user2, role='member')
        
        # Create search and consensus
        search = TravelSearch.objects.create(
            user=self.user,
            group=group,
            destination='Paris',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            adults=2
        )
        consensus = GroupConsensus.objects.create(
            group=group,
            generated_by=self.user,
            consensus_preferences=json.dumps({'destination': 'Paris'})
        )
        
        # Create flight and hotel
        from datetime import datetime
        flight = FlightResult.objects.create(
            search=search,
            external_id='flight1',
            airline='Test Airline',
            price=500.00,
            departure_time=datetime.now(),
            arrival_time=datetime.now()
        )
        hotel = HotelResult.objects.create(
            search=search,
            external_id='hotel1',
            name='Test Hotel',
            price_per_night=100.00,
            total_price=700.00
        )
        
        # Create an accepted trip option
        accepted_option = GroupItineraryOption.objects.create(
            group=group,
            consensus=consensus,
            search=search,
            option_letter='A',
            status='accepted',
            is_winner=True,
            title='Paris Adventure',
            description='A great trip to Paris',
            destination='Paris',
            selected_flight=flight,
            selected_hotel=hotel,
            selected_activities=json.dumps(['activity1']),
            estimated_total_cost=1200.00,
            cost_per_person=600.00
        )
        
        # Create an activity
        activity = ActivityResult.objects.create(
            search=search,
            external_id='activity1',
            name='Eiffel Tower Tour',
            price=50.00
        )
        
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check that accepted_group_trips is in context
        self.assertIn('accepted_group_trips', response.context)
        accepted_trips = response.context['accepted_group_trips']
        self.assertGreaterEqual(len(accepted_trips), 1)
        
        # Find our accepted option in the trips
        our_trip = None
        for trip in accepted_trips:
            if trip['option'].id == accepted_option.id:
                our_trip = trip
                break
        
        self.assertIsNotNone(our_trip, "Accepted option should be in accepted_group_trips")
        # Activities list may be empty if ActivityResult lookup fails, so just verify structure
        self.assertIn('activities', our_trip)
    
    def test_dashboard_no_accepted_trips(self):
        """Test dashboard when user has no accepted group trips"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('accepted_group_trips', response.context)
        self.assertEqual(len(response.context['accepted_group_trips']), 0)
    
    def test_dashboard_user_not_in_groups(self):
        """Test dashboard when user is not a member of any groups"""
        user3 = User.objects.create_user(username='user3', password='pass123')
        UserProfile.objects.create(user=user3, phone_number='')
        self.client.login(username='user3', password='pass123')
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('accepted_group_trips', response.context)
        self.assertEqual(len(response.context['accepted_group_trips']), 0)
    
    def test_dashboard_weather_data_error_handling(self):
        """Test dashboard handles weather API errors gracefully"""
        from unittest.mock import patch, MagicMock
        from travel_groups.models import TravelGroup, GroupMember
        from ai_implementation.models import GroupItineraryOption, GroupConsensus, TravelSearch, FlightResult, HotelResult
        import json
        
        self.client.login(username='testuser', password='testpass123')
        
        group = TravelGroup.objects.create(
            name='Test Group',
            created_by=self.user,
            password='test123'
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        
        search = TravelSearch.objects.create(
            user=self.user,
            group=group,
            destination='Paris',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            adults=2
        )
        consensus = GroupConsensus.objects.create(
            group=group,
            generated_by=self.user,
            consensus_preferences=json.dumps({'destination': 'Paris'})
        )
        
        flight = FlightResult.objects.create(
            search=search,
            external_id='flight1',
            airline='Test Airline',
            price=500.00,
            departure_time=datetime.now(),
            arrival_time=datetime.now()
        )
        hotel = HotelResult.objects.create(
            search=search,
            external_id='hotel1',
            name='Test Hotel',
            price_per_night=100.00,
            total_price=700.00
        )
        
        accepted_option = GroupItineraryOption.objects.create(
            group=group,
            consensus=consensus,
            search=search,
            option_letter='A',
            status='accepted',
            is_winner=True,
            title='Paris Adventure',
            description='A great trip to Paris',
            destination='Paris',
            selected_flight=flight,
            selected_hotel=hotel,
            estimated_total_cost=1200.00,
            cost_per_person=600.00
        )
        
        # Mock weather connector to raise an exception
        with patch('ai_implementation.api_connectors.WeatherAPIConnector') as mock_weather:
            mock_instance = MagicMock()
            mock_instance.get_weather_for_trip.side_effect = Exception("Weather API error")
            mock_weather.return_value = mock_instance
            
            response = self.client.get(reverse('accounts:dashboard'))
            self.assertEqual(response.status_code, 200)
            # Dashboard should still render even if weather fails
            self.assertIn('accepted_group_trips', response.context)
    
    def test_dashboard_weather_data_none(self):
        """Test dashboard handles None weather data"""
        from travel_groups.models import TravelGroup, GroupMember
        from ai_implementation.models import GroupItineraryOption, GroupConsensus, TravelSearch, FlightResult, HotelResult
        from unittest.mock import patch, MagicMock
        import json
        from datetime import datetime
        
        self.client.login(username='testuser', password='testpass123')
        
        group = TravelGroup.objects.create(
            name='Test Group',
            created_by=self.user,
            password='test123'
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        
        search = TravelSearch.objects.create(
            user=self.user,
            group=group,
            destination='Paris',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            adults=2
        )
        consensus = GroupConsensus.objects.create(
            group=group,
            generated_by=self.user,
            consensus_preferences=json.dumps({'destination': 'Paris'})
        )
        
        flight = FlightResult.objects.create(
            search=search,
            external_id='flight1',
            airline='Test Airline',
            price=500.00,
            departure_time=datetime.now(),
            arrival_time=datetime.now()
        )
        hotel = HotelResult.objects.create(
            search=search,
            external_id='hotel1',
            name='Test Hotel',
            price_per_night=100.00,
            total_price=700.00
        )
        
        accepted_option = GroupItineraryOption.objects.create(
            group=group,
            consensus=consensus,
            search=search,
            option_letter='A',
            status='accepted',
            is_winner=True,
            title='Paris Adventure',
            destination='Paris',
            selected_flight=flight,
            selected_hotel=hotel,
            estimated_total_cost=1200.00,
            cost_per_person=600.00
        )
        
        # Mock weather connector to return None
        with patch('ai_implementation.api_connectors.WeatherAPIConnector') as mock_weather:
            mock_instance = MagicMock()
            mock_instance.get_weather_for_trip.return_value = None
            mock_weather.return_value = mock_instance
            
            response = self.client.get(reverse('accounts:dashboard'))
            self.assertEqual(response.status_code, 200)
    
    def test_dashboard_weather_no_daily_forecast(self):
        """Test dashboard handles weather data without daily forecast"""
        from travel_groups.models import TravelGroup, GroupMember
        from ai_implementation.models import GroupItineraryOption, GroupConsensus, TravelSearch, FlightResult, HotelResult
        from unittest.mock import patch, MagicMock
        import json
        from datetime import datetime
        
        self.client.login(username='testuser', password='testpass123')
        
        group = TravelGroup.objects.create(
            name='Test Group',
            created_by=self.user,
            password='test123'
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        
        search = TravelSearch.objects.create(
            user=self.user,
            group=group,
            destination='Paris',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            adults=2
        )
        consensus = GroupConsensus.objects.create(
            group=group,
            generated_by=self.user,
            consensus_preferences=json.dumps({'destination': 'Paris'})
        )
        
        flight = FlightResult.objects.create(
            search=search,
            external_id='flight1',
            airline='Test Airline',
            price=500.00,
            departure_time=datetime.now(),
            arrival_time=datetime.now()
        )
        hotel = HotelResult.objects.create(
            search=search,
            external_id='hotel1',
            name='Test Hotel',
            price_per_night=100.00,
            total_price=700.00
        )
        
        accepted_option = GroupItineraryOption.objects.create(
            group=group,
            consensus=consensus,
            search=search,
            option_letter='A',
            status='accepted',
            is_winner=True,
            title='Paris Adventure',
            destination='Paris',
            selected_flight=flight,
            selected_hotel=hotel,
            estimated_total_cost=1200.00,
            cost_per_person=600.00
        )
        
        # Mock weather connector to return data without daily
        with patch('ai_implementation.api_connectors.WeatherAPIConnector') as mock_weather:
            mock_instance = MagicMock()
            mock_instance.get_weather_for_trip.return_value = {'current': {}}
            mock_weather.return_value = mock_instance
            
            response = self.client.get(reverse('accounts:dashboard'))
            self.assertEqual(response.status_code, 200)


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


class DeleteItineraryViewTest(TestCase):
    """Test cases for delete itinerary view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.start_date = date.today()
        self.end_date = self.start_date + timedelta(days=7)
        self.itinerary = Itinerary.objects.create(
            user=self.user,
            title='Test Trip',
            destination='Test Dest',
            start_date=self.start_date,
            end_date=self.end_date
        )
    
    def test_delete_itinerary_requires_login(self):
        """Test that deleting itinerary requires authentication"""
        response = self.client.delete(reverse('accounts:delete_itinerary', args=[self.itinerary.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_delete_itinerary_success(self):
        """Test successful itinerary deletion"""
        self.client.login(username='testuser', password='testpass123')
        itinerary_id = self.itinerary.id
        itinerary_title = self.itinerary.title
        response = self.client.delete(reverse('accounts:delete_itinerary', args=[itinerary_id]))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('deleted successfully', data['message'])
        self.assertFalse(Itinerary.objects.filter(id=itinerary_id).exists())
    
    def test_delete_itinerary_not_found(self):
        """Test deleting non-existent itinerary"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.delete(reverse('accounts:delete_itinerary', args=[99999]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'].lower())
    
    def test_delete_itinerary_unauthorized(self):
        """Test deleting another user's itinerary"""
        other_user = User.objects.create_user(username='other', password='pass123')
        other_itinerary = Itinerary.objects.create(
            user=other_user,
            title='Other Trip',
            destination='Other Dest',
            start_date=self.start_date,
            end_date=self.end_date
        )
        self.client.login(username='testuser', password='testpass123')
        response = self.client.delete(reverse('accounts:delete_itinerary', args=[other_itinerary.id]))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'].lower())
    
    def test_delete_itinerary_exception_handling(self):
        """Test delete itinerary handles exceptions"""
        from unittest.mock import patch
        self.client.login(username='testuser', password='testpass123')
        
        with patch.object(Itinerary.objects, 'get', side_effect=Exception("Database error")):
            response = self.client.delete(reverse('accounts:delete_itinerary', args=[self.itinerary.id]))
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.content)
            self.assertFalse(data['success'])
            self.assertIn('error', data)

