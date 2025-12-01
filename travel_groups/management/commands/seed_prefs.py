"""
Django management command to seed the database with sample user preferences for travel groups.

Usage:
    python manage.py seed_preferences
    python manage.py seed_preferences --clear
    python manage.py seed_preferences --include-travel-prefs
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from travel_groups.models import TravelGroup, GroupMember, TravelPreference, TripPreference
from django.db import transaction
from django.db.models.signals import post_save
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = "Seeds the database with sample user preferences for existing travel groups"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing preferences before seeding",
        )
        parser.add_argument(
            "--include-travel-prefs",
            action="store_true",
            help="Also create TravelPreference entries (older model)",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        include_travel_prefs = options["include_travel_prefs"]

        # Check if there are group members
        group_members = GroupMember.objects.all()
        if not group_members.exists():
            self.stdout.write(
                self.style.ERROR(
                    'No group members found! Please run "python manage.py seed_groups" first.'
                )
            )
            return

        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing preferences..."))
            TripPreference.objects.all().delete()
            if include_travel_prefs:
                TravelPreference.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared existing preferences"))

        self.stdout.write(f"Creating preferences for {group_members.count()} group memberships...")

        # Sample preference data
        destinations = [
            "Paris, France",
            "Tokyo, Japan",
            "New York, USA",
            "Bali, Indonesia",
            "Barcelona, Spain",
            "Dubai, UAE",
            "Sydney, Australia",
            "Rome, Italy",
            "Bangkok, Thailand",
            "London, UK",
            "Santorini, Greece",
            "Maui, Hawaii",
            "Iceland",
            "Costa Rica",
            "Maldives",
        ]

        budgets = ["$500-1000", "$1000-2000", "$2000-3000", "$3000-5000", "$5000+"]
        budget_values = ["$1000", "$1500", "$2000", "$2500", "$3000", "$4000", "$5000"]

        accommodations = [
            "Hotel",
            "Airbnb",
            "Hostel",
            "Resort",
            "Boutique Hotel",
            "Vacation Rental",
        ]

        activities = [
            "Sightseeing, Museums, Photography",
            "Beach Activities, Swimming, Snorkeling",
            "Hiking, Outdoor Adventures, Nature",
            "Shopping, Dining, Nightlife",
            "Cultural Experiences, Local Tours",
            "Water Sports, Diving, Sailing",
            "Skiing, Snowboarding, Winter Sports",
            "Food Tours, Cooking Classes",
            "Historical Sites, Architecture",
            "Relaxation, Spa, Wellness",
        ]

        dietary_options = [
            "None",
            "Vegetarian",
            "Vegan",
            "Gluten-free",
            "Halal",
            "Kosher",
            "Nut allergies",
            "Lactose intolerant",
        ]

        accessibility_options = [
            "None",
            "Wheelchair accessible",
            "Mobility assistance needed",
            "Visual impairment accommodations",
            "Hearing impairment accommodations",
        ]

        travel_methods = ["flight", "car", "train", "bus", "other"]

        additional_notes = [
            "Prefer early morning flights",
            "Looking forward to trying local cuisine",
            "Need pet-friendly accommodations",
            "Interested in photography opportunities",
            "Would like to visit local markets",
            "Prefer quieter, less touristy areas",
            "Excited about nightlife and entertainment",
            "Want to experience local culture authentically",
            "Prefer eco-friendly and sustainable options",
            "Looking for family-friendly activities",
        ]

        created_trip_prefs = 0
        created_travel_prefs = 0
        skipped_count = 0

        # Temporarily disconnect post_save signal to prevent email notifications during seeding
        from notifications.signals import notify_trip_preference_changes
        post_save.disconnect(notify_trip_preference_changes, sender=TripPreference)
        
        try:
            with transaction.atomic():
                # Group members by group to create coordinated preferences
                groups = TravelGroup.objects.all()
                
                for group in groups:
                    members = group.members.all()
                    
                    # Select a common destination for the group (most likely)
                    group_destination = random.choice(destinations)
                    
                    # Select a common date range for the group
                    start_offset = random.randint(30, 180)  # 1-6 months from now
                    trip_duration = random.randint(3, 14)  # 3-14 days
                    group_start_date = datetime.now().date() + timedelta(days=start_offset)
                    group_end_date = group_start_date + timedelta(days=trip_duration)
                    
                    for member in members:
                        # Create TripPreference (newer model)
                        if TripPreference.objects.filter(group=group, user=member.user).exists():
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Trip preference for {member.user.username} in "{group.name}" already exists, skipping...'
                                )
                            )
                            skipped_count += 1
                        else:
                            # Some members prefer the group destination, others have different ideas
                            destination = group_destination if random.random() < 0.7 else random.choice(destinations)
                            
                            # Some variation in dates but generally aligned
                            if random.random() < 0.8:
                                start_date = group_start_date
                                end_date = group_end_date
                            else:
                                # Different dates
                                start_offset_variation = random.randint(-7, 7)
                                start_date = group_start_date + timedelta(days=start_offset_variation)
                                end_date = start_date + timedelta(days=trip_duration + random.randint(-2, 2))
                            
                            trip_pref = TripPreference.objects.create(
                                group=group,
                                user=member.user,
                                start_date=start_date,
                                end_date=end_date,
                                destination=destination,
                                budget=random.choice(budget_values),
                                travel_method=random.choice(travel_methods),
                                rental_car=random.choice([True, False]),
                                accommodation_preference=random.choice(accommodations),
                                activity_preferences=random.choice(activities),
                                dietary_restrictions=random.choice(dietary_options),
                                accessibility_needs=random.choice(accessibility_options),
                                additional_notes=random.choice(additional_notes) if random.random() < 0.7 else "",
                                is_completed=random.choice([True, True, True, False]),  # 75% completed
                            )
                            
                            # Update the member's has_travel_preferences flag
                            member.has_travel_preferences = True
                            member.save()
                            
                            created_trip_prefs += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Created trip preference for {member.user.username} in "{group.name}"'
                                )
                            )
                        
                        # Optionally create TravelPreference (older model)
                        if include_travel_prefs:
                            if hasattr(member, 'travel_preferences'):
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'Travel preference for {member.user.username} in "{group.name}" already exists, skipping...'
                                    )
                                )
                            else:
                                travel_pref = TravelPreference.objects.create(
                                    member=member,
                                    budget_range=random.choice(budgets),
                                    accommodation_preference=random.choice(accommodations),
                                    activity_preferences=random.choice(activities),
                                    dietary_restrictions=random.choice(dietary_options),
                                    accessibility_needs=random.choice(accessibility_options),
                                    notes=random.choice(additional_notes) if random.random() < 0.7 else "",
                                )
                                created_travel_prefs += 1
        finally:
            # Reconnect the signal
            post_save.connect(notify_trip_preference_changes, sender=TripPreference)

        summary_lines = [
            f"\nSeeding complete!",
            f"Created {created_trip_prefs} trip preferences",
        ]
        
        if include_travel_prefs:
            summary_lines.append(f"Created {created_travel_prefs} travel preferences")
        
        if skipped_count > 0:
            summary_lines.append(f"Skipped {skipped_count} existing preferences")
        
        for line in summary_lines:
            self.stdout.write(self.style.SUCCESS(line))
