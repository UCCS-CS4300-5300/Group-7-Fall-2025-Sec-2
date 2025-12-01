#!/usr/bin/env python
"""
Test script to check what SerpAPI actually returns for activities
Run this to see the actual response structure
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()

import json
from ai_implementation.serpapi_connector import SerpApiActivitiesConnector

print("=" * 80)
print("TESTING SERPAPI ACTIVITY SEARCH")
print("=" * 80)

# Create connector
connector = SerpApiActivitiesConnector()

# Test search
destination = "Alberta"
print(f"\nSearching for activities in: {destination}")
print("-" * 80)

try:
    activities = connector.search_activities(
        destination=destination,
        max_results=3  # Just get a few for testing
    )
    
    print(f"\n✅ Found {len(activities)} activities")
    print("\n" + "=" * 80)
    print("ACTIVITY DATA STRUCTURE:")
    print("=" * 80)
    
    for i, activity in enumerate(activities[:3], 1):
        print(f"\n{i}. {activity.get('name', 'Unknown')}")
        print(f"   Keys in activity dict: {list(activity.keys())}")
        print(f"   Image URL: {activity.get('image_url', '(None)')}")
        print(f"   Has image_url: {bool(activity.get('image_url'))}")
        
        # Show all fields
        print(f"   All fields:")
        for key, value in activity.items():
            if key == 'image_url':
                print(f"      {key}: {value}")
            elif isinstance(value, str) and len(value) > 100:
                print(f"      {key}: {value[:100]}...")
            else:
                print(f"      {key}: {value}")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    activities_with_images = sum(1 for a in activities if a.get('image_url'))
    print(f"Total activities: {len(activities)}")
    print(f"Activities with images: {activities_with_images}")
    print(f"Percentage with images: {activities_with_images/len(activities)*100 if activities else 0:.1f}%")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

