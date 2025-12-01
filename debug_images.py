#!/usr/bin/env python
"""
Debug script to check image URLs in the database
Run with: python manage.py shell < debug_images.py
Or: python debug_images.py (if Django is set up)
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()

from ai_implementation.models import ActivityResult, HotelResult

print("=" * 80)
print("IMAGE URL DEBUG REPORT")
print("=" * 80)

# Check recent activities
print("\n📸 RECENT ACTIVITIES (last 10):")
print("-" * 80)
activities = ActivityResult.objects.order_by('-created_at')[:10]
if activities:
    for i, activity in enumerate(activities, 1):
        print(f"\n{i}. {activity.name}")
        print(f"   ID: {activity.id}")
        print(f"   Image URL: {activity.image_url or '(None/Empty)'}")
        print(f"   Has Image: {bool(activity.image_url)}")
        print(f"   Created: {activity.created_at}")
        print(f"   Is Mock: {activity.is_mock}")
        if activity.image_url:
            print(f"   ✅ Image URL exists")
        else:
            print(f"   ❌ No image URL")
else:
    print("   No activities found in database")

# Check recent hotels
print("\n\n🏨 RECENT HOTELS (last 10):")
print("-" * 80)
hotels = HotelResult.objects.order_by('-created_at')[:10]
if hotels:
    for i, hotel in enumerate(hotels, 1):
        print(f"\n{i}. {hotel.name}")
        print(f"   ID: {hotel.id}")
        print(f"   Image URL: {hotel.image_url or '(None/Empty)'}")
        print(f"   Has Image: {bool(hotel.image_url)}")
        print(f"   Created: {hotel.created_at}")
        print(f"   Is Mock: {hotel.is_mock}")
        if hotel.image_url:
            print(f"   ✅ Image URL exists")
        else:
            print(f"   ❌ No image URL")
else:
    print("   No hotels found in database")

# Statistics
print("\n\n📊 STATISTICS:")
print("-" * 80)
total_activities = ActivityResult.objects.count()
activities_with_images = ActivityResult.objects.exclude(image_url__isnull=True).exclude(image_url='').count()
total_hotels = HotelResult.objects.count()
hotels_with_images = HotelResult.objects.exclude(image_url__isnull=True).exclude(image_url='').count()

print(f"Total Activities: {total_activities}")
print(f"Activities with Images: {activities_with_images} ({activities_with_images/total_activities*100 if total_activities > 0 else 0:.1f}%)")
print(f"Total Hotels: {total_hotels}")
print(f"Hotels with Images: {hotels_with_images} ({hotels_with_images/total_hotels*100 if total_hotels > 0 else 0:.1f}%)")

print("\n" + "=" * 80)
print("To enable debug logging in SerpAPI connector, set environment variable:")
print("  export DEBUG=true")
print("  export DJANGO_DEBUG=true")
print("=" * 80)

