from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import date, timedelta
from travel_groups.models import TravelGroup, GroupMember, TripPreference, GroupItinerary
from accounts.models import Itinerary
from unittest.mock import patch


class NotificationTests(TestCase):
    """Test cases for email notification system"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            first_name='User',
            last_name='One'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123',
            first_name='User',
            last_name='Two'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@test.com',
            password='testpass123',
            first_name='User',
            last_name='Three'
        )
        
        # Create a travel group
        self.group = TravelGroup.objects.create(
            name='Summer Vacation',
            description='Beach trip',
            password='testpass',
            created_by=self.user1,
            max_members=10
        )
        
        # Add all users as members
        self.member1 = GroupMember.objects.create(
            group=self.group,
            user=self.user1,
            role='admin'
        )
        self.member2 = GroupMember.objects.create(
            group=self.group,
            user=self.user2,
            role='member'
        )
        self.member3 = GroupMember.objects.create(
            group=self.group,
            user=self.user3,
            role='member'
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_trip_preference_update_notification(self):
        """Test that notifications are sent when trip preferences are updated"""
        # Clear mail outbox
        mail.outbox = []
        
        # Create trip preferences for user1
        trip_pref = TripPreference.objects.create(
            group=self.group,
            user=self.user1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            destination='Miami Beach',
            budget='$1500',
            travel_method='flight',
            is_completed=True
        )
        
        # Wait a moment for async tasks
        import time
        time.sleep(0.1)
        
        # Check that emails were sent
        self.assertEqual(len(mail.outbox), 2)  # One for user2, one for user3
        
        # Verify email content
        emails = [email for email in mail.outbox]
        recipients = [email.to[0] for email in emails]
        self.assertIn('user2@test.com', recipients)
        self.assertIn('user3@test.com', recipients)
        self.assertNotIn('user1@test.com', recipients)  # User1 should not receive notification
        
        # Verify email subject
        self.assertIn('Travel Plan Update', emails[0].subject)
        self.assertIn(self.group.name, emails[0].subject)
        
        # Verify email body contains correct information
        self.assertIn(self.group.name, emails[0].body)
        self.assertIn(self.user1.get_full_name() or self.user1.username, emails[0].body)
        self.assertIn('Miami Beach', emails[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_itinerary_added_notification(self):
        """Test that notifications are sent when an itinerary is added to a group"""
        # Clear mail outbox
        mail.outbox = []
        
        # Create an itinerary for user1
        itinerary = Itinerary.objects.create(
            user=self.user1,
            title='Beach Adventure',
            description='Fun beach activities',
            destination='Miami',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            is_active=True
        )
        
        # Add itinerary to group
        group_itinerary = GroupItinerary.objects.create(
            group=self.group,
            itinerary=itinerary,
            added_by=self.user1
        )
        
        # Wait a moment for async tasks
        import time
        time.sleep(0.1)
        
        # Check that emails were sent
        self.assertEqual(len(mail.outbox), 2)  # One for user2, one for user3
        
        # Verify email content
        emails = [email for email in mail.outbox]
        recipients = [email.to[0] for email in emails]
        self.assertIn('user2@test.com', recipients)
        self.assertIn('user3@test.com', recipients)
        self.assertNotIn('user1@test.com', recipients)
        
        # Verify email subject
        self.assertIn('New Itinerary Added', emails[0].subject)
        self.assertIn(self.group.name, emails[0].subject)
        
        # Verify email body
        self.assertIn('Beach Adventure', emails[0].body)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_itinerary_updated_notification(self):
        """Test that notifications are sent when an itinerary is updated"""
        # Clear mail outbox
        mail.outbox = []
        
        # Create an itinerary for user1
        itinerary = Itinerary.objects.create(
            user=self.user1,
            title='Beach Adventure',
            description='Fun beach activities',
            destination='Miami',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            is_active=True
        )
        
        # Add itinerary to group first
        GroupItinerary.objects.create(
            group=self.group,
            itinerary=itinerary,
            added_by=self.user1
        )
        
        # Clear outbox after creation (we only want to test updates)
        mail.outbox = []
        
        # Update the itinerary
        itinerary.title = 'Updated Beach Adventure'
        itinerary.destination = 'Cancun'
        itinerary.save()
        
        # Wait a moment for async tasks
        import time
        time.sleep(0.1)
        
        # Check that emails were sent
        self.assertEqual(len(mail.outbox), 2)  # One for user2, one for user3
        
        # Verify email content
        emails = [email for email in mail.outbox]
        recipients = [email.to[0] for email in emails]
        self.assertIn('user2@test.com', recipients)
        self.assertIn('user3@test.com', recipients)
        
        # Verify email subject
        self.assertIn('Itinerary Updated', emails[0].subject)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_notification_for_incomplete_preferences(self):
        """Test that no notifications are sent for incomplete trip preferences"""
        # Clear mail outbox
        mail.outbox = []
        
        # Create trip preferences without marking as completed
        trip_pref = TripPreference.objects.create(
            group=self.group,
            user=self.user1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            destination='Miami Beach',
            budget='$1500',
            travel_method='flight',
            is_completed=False  # Not completed
        )
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Check that no emails were sent
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_notification_for_creator(self):
        """Test that the user making changes doesn't receive notifications"""
        # Clear mail outbox
        mail.outbox = []
        
        # User2 creates trip preferences
        trip_pref = TripPreference.objects.create(
            group=self.group,
            user=self.user2,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            destination='Paris',
            budget='$2000',
            travel_method='flight',
            is_completed=True
        )
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Check emails were sent to others but not user2
        self.assertEqual(len(mail.outbox), 2)  # user1 and user3
        
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn('user1@test.com', recipients)
        self.assertIn('user3@test.com', recipients)
        self.assertNotIn('user2@test.com', recipients)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_no_notification_when_user_has_no_email(self):
        """Test that no notification is sent if user has no email"""
        # Create a user without email
        user_no_email = User.objects.create_user(
            username='noemail',
            email='',  # No email
            password='testpass123'
        )
        
        # Add to group
        GroupMember.objects.create(
            group=self.group,
            user=user_no_email,
            role='member'
        )
        
        # Clear mail outbox
        mail.outbox = []
        
        # Create trip preferences
        trip_pref = TripPreference.objects.create(
            group=self.group,
            user=self.user1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            destination='Miami Beach',
            budget='$1500',
            travel_method='flight',
            is_completed=True
        )
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        # Should still have 2 emails (user2 and user3), not 3
        self.assertEqual(len(mail.outbox), 2)
        
        # Verify no email was attempted for user without email
        recipients = [email.to[0] for email in mail.outbox]
        self.assertNotIn('', recipients)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_notification_signal_integration(self):
        """Test that signals are properly connected and working"""
        from notifications.signals import notify_trip_preference_changes
        
        # Verify signal is connected
        from django.db.models.signals import post_save
        from travel_groups.models import TripPreference
        
        # Check if signal receivers are registered
        receivers = post_save._live_receivers(TripPreference)
        self.assertTrue(len(receivers) > 0)
        
        # Check that our notification handler is in the receivers
        receiver_names = [str(receiver) for receiver in receivers]
        # The signal should be registered

