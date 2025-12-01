"""
Django management command to seed the database with sample travel groups.

Usage:
    python manage.py seed_groups
    python manage.py seed_groups --groups-per-user 3
    python manage.py seed_groups --clear
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from travel_groups.models import TravelGroup, GroupMember
from django.db import transaction
import random


class Command(BaseCommand):
    help = "Seeds the database with sample travel groups for existing users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--groups-per-user",
            type=int,
            default=2,
            help="Number of groups to create per user (default: 2)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing travel groups before seeding",
        )

    def handle(self, *args, **options):
        groups_per_user = options["groups_per_user"]
        clear = options["clear"]

        # Get all users excluding superusers
        users = User.objects.filter(is_superuser=False)

        if not users.exists():
            self.stdout.write(
                self.style.ERROR(
                    'No users found! Please run "python manage.py seed_users" first.'
                )
            )
            return

        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing travel groups..."))
            TravelGroup.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared existing travel groups"))

        self.stdout.write(
            f"Creating {groups_per_user} groups per user for {users.count()} users..."
        )

        # Sample group data templates
        group_templates = [
            {
                "name": "Summer Adventure 2026",
                "description": "Planning an exciting summer getaway with friends and family.",
                "max_members": 8,
            },
            {
                "name": "Beach Paradise Trip",
                "description": "Relaxing beach vacation to unwind and enjoy the sun.",
                "max_members": 6,
            },
            {
                "name": "European Explorers",
                "description": "Exploring the historic cities and cultures of Europe.",
                "max_members": 10,
            },
            {
                "name": "Mountain Retreat",
                "description": "Hiking and camping in the beautiful mountains.",
                "max_members": 8,
            },
            {
                "name": "City Lights Tour",
                "description": "Visiting major cities and experiencing urban culture.",
                "max_members": 7,
            },
            {
                "name": "Weekend Getaway Crew",
                "description": "Quick weekend trips to nearby destinations.",
                "max_members": 5,
            },
            {
                "name": "Food & Culture Expedition",
                "description": "Exploring local cuisines and cultural experiences.",
                "max_members": 6,
            },
            {
                "name": "Adventure Seekers",
                "description": "For those who love extreme sports and outdoor activities.",
                "max_members": 8,
            },
            {
                "name": "Historical Heritage Tour",
                "description": "Visiting museums, monuments, and historical sites.",
                "max_members": 9,
            },
            {
                "name": "Island Hoppers",
                "description": "Exploring tropical islands and enjoying water activities.",
                "max_members": 7,
            },
            {
                "name": "Winter Wonderland Trip",
                "description": "Skiing, snowboarding, and winter sports adventure.",
                "max_members": 8,
            },
            {
                "name": "Safari Expedition",
                "description": "Wildlife viewing and nature photography trip.",
                "max_members": 6,
            },
            {
                "name": "Road Trip Warriors",
                "description": "Epic cross-country road trip with multiple stops.",
                "max_members": 5,
            },
            {
                "name": "Cruise Companions",
                "description": "Planning a cruise vacation together.",
                "max_members": 10,
            },
            {
                "name": "Festival Fanatics",
                "description": "Attending music festivals and cultural events.",
                "max_members": 8,
            },
        ]

        created_count = 0
        users_list = list(users)
        # Track how many groups each user is in (including as admin)
        user_group_count = {user.id: 0 for user in users_list}

        with transaction.atomic():
            for user in users_list:
                for i in range(groups_per_user):
                    # Select a template (cycle through if needed)
                    template_idx = (created_count) % len(group_templates)
                    template = group_templates[template_idx]

                    # Create unique group name
                    group_name = f"{template['name']} - {user.username}"
                    if i > 0:
                        group_name = f"{template['name']} {i+1} - {user.username}"

                    # Create the travel group
                    group = TravelGroup.objects.create(
                        name=group_name,
                        description=template["description"],
                        password="password123",
                        created_by=user,
                        max_members=template["max_members"],
                        is_active=True,
                    )

                    # Add the creator as an admin member
                    GroupMember.objects.create(group=group, user=user, role="admin")
                    user_group_count[user.id] += 1

                    # Add other users as members, but ensure no user is in more than 2 groups
                    num_additional_members = random.randint(
                        1, min(3, len(users_list) - 1)
                    )
                    other_users = [
                        u
                        for u in users_list
                        if u != user and user_group_count[u.id] < 2
                    ]

                    # Only add as many members as possible without exceeding limit
                    num_to_add = min(num_additional_members, len(other_users))
                    if num_to_add > 0:
                        additional_members = random.sample(other_users, num_to_add)

                        for member_user in additional_members:
                            GroupMember.objects.create(
                                group=group, user=member_user, role="member"
                            )
                            user_group_count[member_user.id] += 1

                    created_count += 1
                    member_count = (
                        num_to_add + 1 if num_to_add > 0 else 1
                    )  # +1 for the creator
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created group: "{group_name}" with {member_count} member(s)'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete! Created {created_count} travel groups."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Note: All groups have been assigned the password: password123"
            )
        )
