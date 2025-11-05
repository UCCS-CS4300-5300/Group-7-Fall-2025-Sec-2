#!/usr/bin/env python
"""
API Keys Test Script
Tests both OpenAI and Duffel API connections
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()

from django.conf import settings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=" * 70)
print("🔍 TESTING API KEYS")
print("=" * 70)
print()

# Test 1: Check if keys are loaded
print("📋 Step 1: Checking if API keys are loaded...")
print("-" * 70)

openai_key = settings.OPENAI_API_KEY
duffel_key = settings.DUFFEL_API_KEY

if openai_key:
    print(f"✅ OpenAI Key Found: {openai_key[:15]}...")
else:
    print("❌ OpenAI Key NOT FOUND in environment!")
    print("   Add to .env: OPEN_AI_KEY=sk-your-key")

if duffel_key:
    print(f"✅ Duffel Key Found: {duffel_key[:20]}...")
else:
    print("❌ Duffel Key NOT FOUND in environment!")
    print("   Add to .env: DUFFEL_API_KEY=duffel_test_...")

print()

# Test 2: Test OpenAI API
print("🤖 Step 2: Testing OpenAI API Connection...")
print("-" * 70)

if openai_key:
    try:
        from ai_implementation.openai_service import OpenAIService
        
        print("Connecting to OpenAI API...")
        service = OpenAIService()
        
        print("Asking OpenAI a test question...")
        result = service.answer_travel_question(
            "What is the capital of France?",
            context={"purpose": "API test"}
        )
        
        if result and "Paris" in result:
            print("✅ OpenAI API is WORKING!")
            print(f"   Response: {result[:100]}...")
        else:
            print("⚠️  OpenAI API responded but answer unexpected")
            print(f"   Response: {result}")
    except Exception as e:
        print(f"❌ OpenAI API ERROR: {str(e)}")
        print("   Possible issues:")
        print("   - Invalid API key")
        print("   - No API credits remaining")
        print("   - Network connection problem")
else:
    print("⏭️  Skipping OpenAI test (no key found)")

print()

# Test 3: Test Duffel API
print("✈️  Step 3: Testing Duffel API Connection...")
print("-" * 70)

if duffel_key:
    try:
        from ai_implementation.duffel_connector import DuffelFlightSearch
        
        print("Connecting to Duffel API...")
        duffel = DuffelFlightSearch()
        
        print("Searching for test flights: LAX → JFK...")
        from datetime import datetime, timedelta
        
        # Search for flights 30 days from now
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        return_date = (datetime.now() + timedelta(days=37)).strftime('%Y-%m-%d')
        
        flights = duffel.search_flights(
            origin='LAX',
            destination='JFK',
            departure_date=future_date,
            return_date=return_date,
            adults=1
        )
        
        if flights:
            print(f"✅ Duffel API is WORKING!")
            print(f"   Found {len(flights)} flight(s)")
            
            # Check if real or mock data
            first_flight = flights[0]
            if first_flight.get('is_mock'):
                print("⚠️  WARNING: Returning MOCK data (not real Duffel data)")
                print("   This means the API key might be invalid or API call failed")
                print("   Check your Duffel API key")
            else:
                print(f"   ✅ REAL Duffel data received!")
                print(f"   First flight: {first_flight.get('airline_name', 'Unknown')} - ${first_flight.get('price', 0)}")
                print(f"   Route: {first_flight.get('route', 'N/A')}")
        else:
            print("❌ No flights returned")
            
    except Exception as e:
        print(f"❌ Duffel API ERROR: {str(e)}")
        print("   Possible issues:")
        print("   - Invalid API key format")
        print("   - Network connection problem")
        print("   - Duffel API service issue")
else:
    print("⏭️  Skipping Duffel test (no key found)")
    print("   The system will use mock data for flights")

print()
print("=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)

summary = []

if openai_key:
    summary.append("OpenAI: Configured")
else:
    summary.append("OpenAI: ❌ NOT configured")

if duffel_key:
    summary.append("Duffel: Configured")
else:
    summary.append("Duffel: ⚠️  NOT configured (will use mock data)")

for item in summary:
    print(f"  {item}")

print()
print("💡 NEXT STEPS:")
print()

if not openai_key:
    print("  ❌ OpenAI key required! Add to .env:")
    print("     OPEN_AI_KEY=sk-your-key")
    print()

if not duffel_key:
    print("  ⚠️  Duffel key recommended (optional):")
    print("     DUFFEL_API_KEY=duffel_test_your-key")
    print("     Without it, system uses mock flight data")
    print()

if openai_key and duffel_key:
    print("  ✅ Both APIs configured!")
    print("  ✅ Ready to use 'Find Your Trip' feature!")
    print()
    print("  Test it:")
    print("  1. python manage.py runserver")
    print("  2. Go to group page")
    print("  3. Click 'Manage Trips' tab")
    print("  4. Click 'Find Your Trip' button")
    print()

print("=" * 70)
print("Test complete!")
print("=" * 70)


