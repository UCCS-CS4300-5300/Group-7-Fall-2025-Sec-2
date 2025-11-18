#!/usr/bin/env python
"""
API Keys Test Script
Tests OpenAI, SerpAPI (Google Flights), and Duffel API connections
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
serpapi_key = settings.SERP_API_KEY
hotel_api_key = settings.HOTEL_API_KEY

if openai_key:
    key_preview = openai_key[:15] if len(openai_key) > 15 else openai_key
    print(f"✅ OpenAI Key Found: {key_preview}...")
else:
    print("❌ OpenAI Key NOT FOUND in environment!")
    print("   Add to .env: OPEN_AI_KEY=sk-your-key")

if serpapi_key:
    key_preview = serpapi_key[:20] if len(serpapi_key) > 20 else serpapi_key
    print(f"✅ SerpAPI Key Found: {key_preview}...")
else:
    print("❌ SerpAPI Key NOT FOUND in environment!")
    print("   Add to .env: SERP_API_KEY=your-serpapi-key")
    print("   Get your key from: https://serpapi.com/")

if hotel_api_key:
    key_preview = hotel_api_key[:20] if len(hotel_api_key) > 20 else hotel_api_key
    print(f"✅ Makcorps Hotel API Key Found: {key_preview}...")
else:
    print("❌ Makcorps Hotel API Key NOT FOUND in environment!")
    print("   Add to .env: HOTEL_API_KEY=your-makcorps-key")
    print("   Get your key from: https://api.makcorps.com/free")

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

# Note: Duffel API has been removed - all services now use SerpAPI and Makcorps
print("ℹ️  Step 3: API Configuration")
print("-" * 70)
print("   ✅ Flights: SerpAPI (Google Flights)")
print("   ✅ Hotels: Makcorps API")
print("   ✅ Activities: SerpAPI (Google Search)")
print("   ℹ️  Duffel API has been removed from the project")
print()

# Test 3: Test Makcorps Hotel API
print("🏨 Step 3: Testing Makcorps Hotel API Connection...")
print("-" * 70)

if hotel_api_key:
    try:
        from ai_implementation.makcorps_connector import MakcorpsHotelConnector
        from datetime import datetime, timedelta
        
        print("Connecting to Makcorps Hotel API...")
        makcorps = MakcorpsHotelConnector()
        
        print("Searching for test hotels in New York...")
        
        # Search for hotels 30 days from now
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        checkout_date = (datetime.now() + timedelta(days=33)).strftime('%Y-%m-%d')
        
        hotels = makcorps.search_hotels(
            location='New York',
            check_in=future_date,
            check_out=checkout_date,
            adults=2,
            rooms=1,
            max_results=5
        )
        
        if hotels:
            print(f"✅ Makcorps Hotel API is WORKING!")
            print(f"   Found {len(hotels)} hotel(s)")
            
            # Check if real or mock data
            first_hotel = hotels[0]
            if first_hotel.get('is_mock'):
                print("⚠️  WARNING: Returning MOCK data (not real Makcorps data)")
                print("   This means the API key might be invalid or API call failed")
                print("   Check your HOTEL_API_KEY")
            else:
                print(f"   ✅ REAL Makcorps data received!")
                print(f"   First hotel: {first_hotel.get('name', 'Unknown')} - ${first_hotel.get('price_per_night', 0)}/night")
                if first_hotel.get('rating'):
                    print(f"   Rating: ⭐ {first_hotel.get('rating')}/5")
        else:
            print("❌ No hotels returned")
            
    except Exception as e:
        print(f"❌ Makcorps Hotel API ERROR: {str(e)}")
        print("   Possible issues:")
        print("   - Invalid API key format")
        print("   - Network connection problem")
        print("   - Makcorps API service issue")
        print("   - Check API documentation at: https://api.makcorps.com/free")
else:
    print("⏭️  Skipping Makcorps test (no key found)")
    print("   ⚠️  WARNING: System will use MOCK data for hotels without Makcorps API key")
    print("   Get your free key from: https://api.makcorps.com/free")

print()

# Test 4: Test SerpAPI (Google Flights)
print("✈️  Step 4: Testing SerpAPI (Google Flights) Connection...")
print("-" * 70)

if serpapi_key:
    try:
        from ai_implementation.serpapi_connector import SerpApiFlightsConnector
        from datetime import datetime, timedelta
        
        print("Connecting to SerpAPI...")
        serpapi = SerpApiFlightsConnector()
        
        print("Searching for test flights: LAX → JFK...")
        
        # Search for flights 30 days from now
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        return_date = (datetime.now() + timedelta(days=37)).strftime('%Y-%m-%d')
        
        flights = serpapi.search_flights(
            origin='LAX',
            destination='JFK',
            departure_date=future_date,
            return_date=return_date,
            adults=1,
            max_results=5
        )
        
        if flights:
            print(f"✅ SerpAPI is WORKING!")
            print(f"   Found {len(flights)} flight(s)")
            
            # Check if real or mock data
            first_flight = flights[0]
            if first_flight.get('is_mock'):
                print("⚠️  WARNING: Returning MOCK data (not real SerpAPI data)")
                print("   This means the API key might be invalid or API call failed")
                print("   Check your SerpAPI key at https://serpapi.com/")
            else:
                print(f"   ✅ REAL SerpAPI data received!")
                print(f"   First flight: {first_flight.get('airline_name', 'Unknown')} - ${first_flight.get('price', 0)}")
                print(f"   Route: {first_flight.get('route', 'N/A')}")
        else:
            print("❌ No flights returned")
            
    except Exception as e:
        print(f"❌ SerpAPI ERROR: {str(e)}")
        print("   Possible issues:")
        print("   - Invalid API key format")
        print("   - No API credits remaining (check https://serpapi.com/)")
        print("   - Network connection problem")
        print("   - SerpAPI service issue")
else:
    print("⏭️  Skipping SerpAPI flights test (no key found)")
    print("   ⚠️  WARNING: System will use MOCK data for flights without SerpAPI key")
    print("   Get your free key from: https://serpapi.com/ (100 searches/month free)")

print()

# Test 5: Test SerpAPI Activities
print("🎭 Step 5: Testing SerpAPI Activities (Things to Do) Connection...")
print("-" * 70)

if serpapi_key:
    try:
        from ai_implementation.serpapi_connector import SerpApiActivitiesConnector
        
        print("Connecting to SerpAPI for activities...")
        serpapi_activities = SerpApiActivitiesConnector()
        
        print("Searching for activities in New York...")
        
        activities = serpapi_activities.search_activities(
            destination='New York',
            max_results=5
        )
        
        if activities:
            print(f"✅ SerpAPI Activities is WORKING!")
            print(f"   Found {len(activities)} activity/activities")
            
            # Check if real or mock data
            first_activity = activities[0]
            if first_activity.get('is_mock'):
                print("⚠️  WARNING: Returning MOCK data (not real SerpAPI data)")
                print("   This means the API key might be invalid or API call failed")
                print("   Check your SerpAPI key at https://serpapi.com/")
            else:
                print(f"   ✅ REAL SerpAPI data received!")
                print(f"   First activity: {first_activity.get('name', 'Unknown')}")
                if first_activity.get('rating'):
                    print(f"   Rating: ⭐ {first_activity.get('rating')}/5")
        else:
            print("❌ No activities returned")
            
    except Exception as e:
        print(f"❌ SerpAPI Activities ERROR: {str(e)}")
        print("   Possible issues:")
        print("   - Invalid API key format")
        print("   - No API credits remaining (check https://serpapi.com/)")
        print("   - Network connection problem")
        print("   - SerpAPI service issue")
else:
    print("⏭️  Skipping SerpAPI activities test (no key found)")
    print("   ⚠️  WARNING: System will use MOCK data for activities without SerpAPI key")
    print("   Note: Activities use the same SerpAPI key as flights")

print()
print("=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)

summary = []

if openai_key:
    summary.append("OpenAI: ✅ Configured")
else:
    summary.append("OpenAI: ❌ NOT configured")

if serpapi_key:
    summary.append("SerpAPI (Flights): ✅ Configured")
else:
    summary.append("SerpAPI (Flights): ❌ NOT configured (will use mock data)")

if hotel_api_key:
    summary.append("Makcorps (Hotels): ✅ Configured")
else:
    summary.append("Makcorps (Hotels): ❌ NOT configured (will use mock data)")

# Note: Activities use SerpAPI (same key as flights)
if serpapi_key:
    summary.append("SerpAPI (Activities): ✅ Configured (uses same key as flights)")
else:
    summary.append("SerpAPI (Activities): ❌ NOT configured (will use mock data)")

for item in summary:
    print(f"  {item}")

print()
print("💡 NEXT STEPS:")
print()

if not openai_key:
    print("  ❌ OpenAI key required! Add to .env:")
    print("     OPEN_AI_KEY=sk-your-key")
    print()

if not serpapi_key:
    print("  ❌ SerpAPI key required for real flight data! Add to .env:")
    print("     SERP_API_KEY=your-serpapi-key")
    print("     Get your free key from: https://serpapi.com/")
    print("     (100 searches/month free)")
    print()

if not hotel_api_key:
    print("  ❌ Makcorps Hotel API key required for real hotel data! Add to .env:")
    print("     HOTEL_API_KEY=your-makcorps-key")
    print("     Get your free key from: https://api.makcorps.com/free")
    print()

if not serpapi_key:
    print("  ⚠️  Note: Activities also use SerpAPI (same key as flights)")
    print()

if openai_key and serpapi_key and hotel_api_key:
    print("  ✅ Required APIs configured!")
    print("  ✅ Ready to use 'Find Your Trip' feature!")
    print()
    print("  Test it:")
    print("  1. python manage.py runserver")
    print("  2. Go to group page")
    print("  3. Click 'Find A Trip' tab")
    print("  4. Click 'Find Your Trip' button")
    print()
elif openai_key and serpapi_key:
    print("  ⚠️  Makcorps Hotel API key missing - hotels will use mock data")
    print("  Get your free Makcorps key from: https://api.makcorps.com/free")
    print()
elif openai_key and hotel_api_key:
    print("  ⚠️  SerpAPI key missing - flights will use mock data")
    print("  Get your free SerpAPI key from: https://serpapi.com/")
    print()
elif openai_key:
    print("  ⚠️  Missing API keys - flights and hotels will use mock data")
    print()
elif serpapi_key or hotel_api_key:
    print("  ⚠️  OpenAI key missing - AI features won't work")
    print()
else:
    print("  ❌ Missing required API keys!")
    print()

print("=" * 70)
print("Test complete!")
print("=" * 70)


