#!/usr/bin/env python
"""
Diagnostic script to check group trips in database.
Run with: python CHECK_TRIPS_DEBUG.py
"""

import os
import django

from travel_groups.models import TravelGroup, GroupItinerary
from accounts.models import Itinerary

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()


def check_trips():
    """Check all trips in database"""

    print("=" * 70)
    print("🔍 CHECKING GROUP TRIPS IN DATABASE")
    print("=" * 70)
    print()

    # Get all groups
    groups = TravelGroup.objects.all()

    if not groups:
        print("❌ No groups found in database!")
        print("   Create a group first at: /groups/create/")
        return

    print(f"📊 Found {groups.count()} group(s) in database\n")

    for group in groups:
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📁 Group: {group.name}")
        print(f"   ID: {group.id}")
        print(f"   Created by: {group.created_by.username}")
        print(f"   Members: {group.member_count}")
        print()

        # Get trips for this group
        group_itineraries = GroupItinerary.objects.filter(
            group=group
        ).select_related('itinerary', 'added_by')

        if group_itineraries.count() == 0:
            print("   ⚠️  NO TRIPS in this group")
            print(f"   Create trips at: /groups/{group.id}/trips/")
        else:
            print(f"   ✅ {group_itineraries.count()} trip(s) found:")
            print()

            for i, gi in enumerate(group_itineraries, 1):
                print(f"   {i}. {gi.itinerary.title}")
                print(f"      Destination: {gi.itinerary.destination}")
                print(f"      Dates: {gi.itinerary.start_date} to {gi.itinerary.end_date}")
                print(f"      Added by: {gi.added_by.username}")
                print(f"      Added at: {gi.added_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"      Approved: {'Yes' if gi.is_approved else 'No'}")
                print(f"      Itinerary ID: {gi.itinerary.id}")
                print(f"      GroupItinerary ID: {gi.id}")
                print()

        print()

    # Check for orphaned itineraries (not linked to any group)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🔍 CHECKING FOR UNLINKED ITINERARIES")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    all_itineraries = Itinerary.objects.all()
    linked_itinerary_ids = GroupItinerary.objects.values_list('itinerary_id', flat=True)
    unlinked_itineraries = all_itineraries.exclude(id__in=linked_itinerary_ids)

    print(f"📊 Total itineraries in database: {all_itineraries.count()}")
    print(f"   Linked to groups: {len(linked_itinerary_ids)}")
    print(f"   Personal only (not in groups): {unlinked_itineraries.count()}")
    print()

    if unlinked_itineraries.exists():
        print("📝 Personal itineraries (not in any group):")
        for itin in unlinked_itineraries[:10]:  # Show first 10
            print(f"   - {itin.title} by {itin.user.username}")
        if unlinked_itineraries.count() > 10:
            print(f"   ... and {unlinked_itineraries.count() - 10} more")

    print()
    print("=" * 70)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 70)
    print()
    print("💡 TIPS:")
    print("   - If trips are missing, check they were created successfully")
    print("   - Look for print statements in server logs when creating trips")
    print("   - Verify GroupItinerary link was created")
    print("   - Check if trips appear in Django admin: /admin/")
    print()


if __name__ == '__main__':
    check_trips()
