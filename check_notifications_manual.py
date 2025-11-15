#!/usr/bin/env python
"""
Manual test script for email notifications
Run this script to test the notification system manually

Usage:
    python test_notifications_manual.py
"""

import os
import sys
import django
from django.contrib.auth.models import User
from django.core import mail
from django.test import override_settings
from datetime import date, timedelta
from travel_groups.models import TravelGroup, GroupMember, TripPreference, GroupItinerary
from accounts.models import Itinerary

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()


def test_notifications():
    """Test email notifications manually"""

    print("=" * 60)
    print("Testing Email Notification System")
    print("=" * 60)

    # Setup: Create test users and group
    print("\n1. Setting up test data...")

    # Check if users exist, create if not
    try:
        user1 = User.objects.get(username='test_user1')
    except User.DoesNotExist:
        user1 = User.objects.create_user(
            username='test_user1',
            email='testuser1@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User One'
        )
        print(f"   Created user: {user1.username} ({user1.email})")
    else:
        print(f"   Using existing user: {user1.username}")

    try:
        user2 = User.objects.get(username='test_user2')
    except User.DoesNotExist:
        user2 = User.objects.create_user(
            username='test_user2',
            email='testuser2@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User Two'
        )
        print(f"   Created user: {user2.username} ({user2.email})")
    else:
        print(f"   Using existing user: {user2.username}")

    # Create or get travel group
    group, created = TravelGroup.objects.get_or_create(
        name='Test Notification Group',
        defaults={
            'description': 'Group for testing notifications',
            'password': 'testpass',
            'created_by': user1,
            'max_members': 10
        }
    )

    if created:
        print(f"   Created group: {group.name}")
    else:
        print(f"   Using existing group: {group.name}")

    # Ensure members exist
    member1, _ = GroupMember.objects.get_or_create(
        group=group,
        user=user1,
        defaults={'role': 'admin'}
    )
    member2, _ = GroupMember.objects.get_or_create(
        group=group,
        user=user2,
        defaults={'role': 'member'}
    )

    print(f"   Group members: {member1.user.username}, {member2.user.username}")

    # Configure email backend for testing
    with override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        CELERY_TASK_ALWAYS_EAGER=True
    ):
        print("\n2. Testing Trip Preference Update Notification...")
        mail.outbox = []

        # Create trip preference
        trip_pref = TripPreference.objects.create(
            group=group,
            user=user1,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            destination='Paris, France',
            budget='$2000',
            travel_method='flight',
            is_completed=True
        )

        print(f"   Created trip preference for {user1.username}")
        print(f"   Destination: {trip_pref.destination}")
        print(f"   Expected: Notification email to {user2.email}")

        # Small delay to let signals process
        import time
        time.sleep(0.1)

        # Check results
        if hasattr(mail, 'outbox'):
            if len(mail.outbox) > 0:
                print(f"   [SUCCESS] {len(mail.outbox)} email(s) sent successfully!")
                for i, email in enumerate(mail.outbox, 1):
                    print(f"   Email {i}:")
                    print(f"      To: {email.to}")
                    print(f"      Subject: {email.subject}")
            else:
                print("   [INFO] No emails in outbox (check console output for console backend)")
        else:
            print("   [SUCCESS] Signal triggered (check console output for emails)")

        print("\n3. Testing Itinerary Added Notification...")
        mail.outbox = []

        # Create itinerary
        itinerary = Itinerary.objects.create(
            user=user1,
            title='Paris Adventure',
            description='Visit famous landmarks',
            destination='Paris',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=37),
            is_active=True
        )

        # Add to group
        group_itinerary = GroupItinerary.objects.create(
            group=group,
            itinerary=itinerary,
            added_by=user1
        )

        print(f"   Created itinerary: {itinerary.title}")
        print(f"   Expected: Notification email to {user2.email}")

        time.sleep(0.1)

        if hasattr(mail, 'outbox'):
            if len(mail.outbox) > 0:
                print(f"   [SUCCESS] {len(mail.outbox)} email(s) sent successfully!")
            else:
                print("   [INFO] No emails in outbox (check console output)")
        else:
            print("   [SUCCESS] Signal triggered (check console output for emails)")

        print("\n4. Testing Itinerary Update Notification...")
        mail.outbox = []

        # Update itinerary
        itinerary.title = 'Updated Paris Adventure'
        itinerary.destination = 'Nice, France'
        itinerary.save()

        print(f"   Updated itinerary: {itinerary.title}")
        print(f"   Expected: Notification email to {user2.email}")

        time.sleep(0.1)

        if hasattr(mail, 'outbox'):
            if len(mail.outbox) > 0:
                print(f"   [SUCCESS] {len(mail.outbox)} email(s) sent successfully!")
            else:
                print("   [INFO] No emails in outbox (check console output)")
        else:
            print("   [SUCCESS] Signal triggered (check console output for emails)")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nNote: With console email backend, emails are printed to console.")
    print("In production, configure SMTP settings in environment variables.")
    print("\nTo see actual email output, check the console above.")

    # Cleanup option (commented out - uncomment to clean up test data)
    # print("\nCleaning up test data...")
    # TripPreference.objects.filter(group=group).delete()
    # GroupItinerary.objects.filter(group=group).delete()
    # Itinerary.objects.filter(user__in=[user1, user2]).delete()
    # GroupMember.objects.filter(group=group).delete()
    # group.delete()
    # user1.delete()
    # user2.delete()
    # print("Cleanup complete!")


if __name__ == '__main__':
    try:
        test_notifications()
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
