#!/usr/bin/env python
"""
Debug script for "Find Your Trip" feature
Checks what's happening when you click the button
"""

import os
import django
from travel_groups.models import TravelGroup, TripPreference
from ai_implementation.models import GroupConsensus, GroupItineraryOption, ItineraryVote

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()

print("=" * 70)
print("🔍 DEBUGGING 'FIND YOUR TRIP' FEATURE")
print("=" * 70)
print()

# Get all groups
groups = TravelGroup.objects.all()

if not groups:
    print("❌ No groups found!")
    print("   Create a group first at: /groups/create/")
    exit()

print(f"📊 Found {groups.count()} group(s)\n")

for group in groups:
    print("━" * 70)
    print(f"📁 GROUP: {group.name}")
    print(f"   ID: {group.id}")
    print(f"   Members: {group.member_count}")
    print()

    # Check trip preferences
    trip_prefs = TripPreference.objects.filter(group=group, is_completed=True)
    print(f"   📝 Trip Preferences: {trip_prefs.count()} completed")

    if trip_prefs.count() < 2:
        print("   ⚠️  ISSUE: Need at least 2 members with preferences!")
        print(f"      Currently have: {trip_prefs.count()}")
        print("      Need: 2 or more")
        print()
        print("   🔧 FIX: Have more members submit preferences at:")
        print(f"      /groups/{group.id}/add-trip-preferences/")
        print()
    else:
        print("   ✅ Enough preferences to generate options")
        print()
        print("   Preference Details:")
        for i, pref in enumerate(trip_prefs, 1):
            print(f"   {i}. {pref.user.username}:")
            print(f"      Destination: {pref.destination}")
            print(f"      Dates: {pref.start_date} to {pref.end_date}")
            print(f"      Budget: {pref.budget}")
        print()

    # Check if voting options exist
    consensus = GroupConsensus.objects.filter(group=group, is_active=True).order_by('-created_at').first()

    if consensus:
        print(f"   📊 Group Consensus: ✅ EXISTS (created {consensus.created_at})")

        options = GroupItineraryOption.objects.filter(group=group, consensus=consensus)
        print(f"   🗳️  Voting Options: {options.count()} options")

        if options.count() == 3:
            print("   ✅ All 3 options created successfully!")
            print()
            for opt in options:
                print(f"   Option {opt.option_letter}: {opt.title}")
                print(f"      Cost: ${opt.estimated_total_cost} (${opt.cost_per_person}/person)")
                print(f"      Votes: {opt.vote_count}")
                if opt.selected_flight:
                    print(f"      Flight: {opt.selected_flight.airline} - ${opt.selected_flight.price}")
                if opt.selected_hotel:
                    print(f"      Hotel: {opt.selected_hotel.name} - ${opt.selected_hotel.total_price}")
                print()
        else:
            print(f"   ⚠️  ISSUE: Expected 3 options, found {options.count()}")
            print("   Try regenerating by clicking 'Find Your Trip' again")
            print()

        # Check votes
        votes = ItineraryVote.objects.filter(group=group)
        print(f"   📊 Votes Cast: {votes.count()} of {group.member_count} members")
        if votes.exists():
            for vote in votes:
                print(f"      - {vote.user.username} voted for Option {vote.option.option_letter}")
        print()

    else:
        print("   ⚠️  No voting options generated yet")
        print("   This is normal if you haven't clicked 'Find Your Trip' yet")
        print()
        print("   🔧 TO GENERATE OPTIONS:")
        print("      1. Ensure 2+ members have submitted preferences")
        print("      2. Go to group page → 'Manage Trips' tab")
        print("      3. Click 'Find Your Trip' button")
        print("      4. Wait 30-60 seconds")
        print()

print()
print("=" * 70)
print("🔍 DIAGNOSTIC COMPLETE")
print("=" * 70)
print()

# Summary
print("📋 SUMMARY:")
print()

all_groups_ok = True
for group in groups:
    prefs_ok = TripPreference.objects.filter(group=group, is_completed=True).count() >= 2
    consensus_exists = GroupConsensus.objects.filter(group=group, is_active=True).exists()

    print(f"Group: {group.name}")
    print(f"  Preferences: {'✅ OK' if prefs_ok else '❌ Need more'}")
    print(f"  Options Generated: {'✅ Yes' if consensus_exists else '⏳ Not yet'}")
    print()

    if not prefs_ok:
        all_groups_ok = False

if all_groups_ok:
    print("✅ All groups ready for 'Find Your Trip'!")
else:
    print("⚠️  Some groups need more member preferences")

print()
print("💡 NEXT STEPS:")
print()
print("  If you clicked 'Find Your Trip' and nothing happened:")
print("  1. Check browser console for JavaScript errors (F12)")
print("  2. Check server logs for error messages")
print("  3. Verify you're redirected to 'Trips' tab")
print("  4. Try clicking the button again")
print()
print("  If options generated but not showing:")
print("  1. Hard refresh browser (Ctrl+Shift+R)")
print("  2. Check this script shows options exist")
print("  3. Check server logs for template errors")
print()
