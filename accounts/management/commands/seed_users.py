"""
Django management command to seed the database with sample users.

Usage:
    python manage.py seed_users
    python manage.py seed_users --count 20
    python manage.py seed_users --clear
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from django.db import transaction


class Command(BaseCommand):
    help = "Seeds the database with sample users and user profiles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of users to create (default: 10)",
        )
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing users before seeding"
        )

    def handle(self, *args, **options):
        count = options["count"]
        clear = options["clear"]

        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing users..."))
            # Delete all users except superusers
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS("Cleared existing users"))

        self.stdout.write(f"Seeding {count} users...")

        # Sample user data
        sample_users = [
            {
                "username": "john_doe",
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+15551234567",
            },
            {
                "username": "jane_smith",
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+15551234568",
            },
            {
                "username": "bob_johnson",
                "email": "bob.johnson@example.com",
                "first_name": "Bob",
                "last_name": "Johnson",
                "phone": "+15551234569",
            },
            {
                "username": "alice_williams",
                "email": "alice.williams@example.com",
                "first_name": "Alice",
                "last_name": "Williams",
                "phone": "+15551234570",
            },
            {
                "username": "charlie_brown",
                "email": "charlie.brown@example.com",
                "first_name": "Charlie",
                "last_name": "Brown",
                "phone": "+15551234571",
            },
            {
                "username": "diana_prince",
                "email": "diana.prince@example.com",
                "first_name": "Diana",
                "last_name": "Prince",
                "phone": "+15551234572",
            },
            {
                "username": "edward_norton",
                "email": "edward.norton@example.com",
                "first_name": "Edward",
                "last_name": "Norton",
                "phone": "+15551234573",
            },
            {
                "username": "fiona_apple",
                "email": "fiona.apple@example.com",
                "first_name": "Fiona",
                "last_name": "Apple",
                "phone": "+15551234574",
            },
            {
                "username": "george_martin",
                "email": "george.martin@example.com",
                "first_name": "George",
                "last_name": "Martin",
                "phone": "+15551234575",
            },
            {
                "username": "hannah_montana",
                "email": "hannah.montana@example.com",
                "first_name": "Hannah",
                "last_name": "Montana",
                "phone": "+15551234576",
            },
        ]

        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for i in range(count):
                # Cycle through sample users if count is larger than sample data
                user_data = sample_users[i % len(sample_users)]

                # Make username unique if we're creating more users than samples
                username = user_data["username"]
                email = user_data["email"]

                if i >= len(sample_users):
                    username = f"{username}_{i}"
                    email_parts = email.split("@")
                    email = f"{email_parts[0]}_{i}@{email_parts[1]}"

                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(
                        self.style.WARNING(
                            f'User "{username}" already exists, skipping...'
                        )
                    )
                    skipped_count += 1
                    continue

                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password="password123",  # Default password for all seed users
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                )

                # Create user profile
                phone = user_data["phone"]
                if i >= len(sample_users):
                    # Modify phone number to make it unique
                    phone = f"+1555{1234567 + i}"

                UserProfile.objects.create(user=user, phone_number=phone)

                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created user: {username} ({email})")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete! Created {created_count} users, skipped {skipped_count}."
            )
        )
        self.stdout.write(
            self.style.WARNING("Default password for all users: password123")
        )
