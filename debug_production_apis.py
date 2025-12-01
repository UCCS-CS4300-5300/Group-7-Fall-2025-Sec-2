#!/usr/bin/env python
"""
Production API Diagnostic Script
Tests SerpAPI and OpenAI connections to identify issues in production
"""

import os
import sys
import django
import traceback
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupgo.settings')
django.setup()

from django.conf import settings

print("=" * 80)
print("🔍 PRODUCTION API DIAGNOSTIC TOOL")
print("=" * 80)
print()

# Check environment variables
print("📋 Step 1: Checking Environment Variables...")
print("-" * 80)

serpapi_key = os.environ.get('SERP_API_KEY', '')
openai_key = os.environ.get('OPENAI_API_KEY', '') or os.environ.get('OPEN_AI_KEY', '')

print(f"SERP_API_KEY: {'✅ SET' if serpapi_key else '❌ NOT SET'} ({'***' + serpapi_key[-4:] if serpapi_key else 'N/A'})")
print(f"OPENAI_API_KEY: {'✅ SET' if openai_key else '❌ NOT SET'} ({'***' + openai_key[-4:] if openai_key else 'N/A'})")
print()

# Check Django settings
print("📋 Step 2: Checking Django Settings...")
print("-" * 80)

settings_serpapi = getattr(settings, 'SERP_API_KEY', '')
settings_openai = getattr(settings, 'OPENAI_API_KEY', '')

print(f"settings.SERP_API_KEY: {'✅ SET' if settings_serpapi else '❌ NOT SET'}")
print(f"settings.OPENAI_API_KEY: {'✅ SET' if settings_openai else '❌ NOT SET'}")
print()

# Test SerpAPI Flights
print("✈️  Step 3: Testing SerpAPI Flights...")
print("-" * 80)

try:
    from ai_implementation.serpapi_connector import SerpApiFlightsConnector
    
    serpapi_flights = SerpApiFlightsConnector()
    
    # Check if API key is configured
    if not serpapi_flights.api_key:
        print("❌ ERROR: SerpAPI key not found in connector!")
        print("   This means the connector will use mock data")
    else:
        print(f"✅ SerpAPI key found: ***{serpapi_flights.api_key[-4:]}")
        
        # Test a real API call
        test_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        return_date = (datetime.now() + timedelta(days=37)).strftime('%Y-%m-%d')
        
        print(f"Testing flight search: LAX → JFK on {test_date}")
        
        try:
            flights = serpapi_flights.search_flights(
                origin='LAX',
                destination='JFK',
                departure_date=test_date,
                return_date=return_date,
                adults=1,
                max_results=3
            )
            
            if flights:
                print(f"✅ SerpAPI returned {len(flights)} flight(s)")
                
                # Check if mock data
                if flights[0].get('is_mock'):
                    print("⚠️  WARNING: Returning MOCK data!")
                    print("   This indicates the API call failed or key is invalid")
                    print("   Possible reasons:")
                    print("   - Invalid API key")
                    print("   - No API credits remaining")
                    print("   - API rate limit exceeded")
                    print("   - Network/connection issue")
                else:
                    print("✅ REAL SerpAPI data received!")
                    first_flight = flights[0]
                    print(f"   First flight: {first_flight.get('airline_name', 'Unknown')} - ${first_flight.get('price', 0)}")
            else:
                print("❌ No flights returned")
                
        except Exception as e:
            print(f"❌ ERROR during flight search: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            
except Exception as e:
    print(f"❌ ERROR initializing SerpAPI connector: {str(e)}")
    traceback.print_exc()

print()

# Test SerpAPI Activities
print("🎭 Step 4: Testing SerpAPI Activities...")
print("-" * 80)

try:
    from ai_implementation.serpapi_connector import SerpApiActivitiesConnector
    
    serpapi_activities = SerpApiActivitiesConnector()
    
    if not serpapi_activities.api_key:
        print("❌ ERROR: SerpAPI key not found in connector!")
    else:
        print(f"✅ SerpAPI key found: ***{serpapi_activities.api_key[-4:]}")
        
        print("Testing activity search: New York")
        
        try:
            activities = serpapi_activities.search_activities(
                destination='New York',
                max_results=3
            )
            
            if activities:
                print(f"✅ SerpAPI returned {len(activities)} activity/activities")
                
                if activities[0].get('is_mock'):
                    print("⚠️  WARNING: Returning MOCK data!")
                else:
                    print("✅ REAL SerpAPI data received!")
                    first_activity = activities[0]
                    print(f"   First activity: {first_activity.get('name', 'Unknown')}")
            else:
                print("❌ No activities returned")
                
        except Exception as e:
            print(f"❌ ERROR during activity search: {str(e)}")
            traceback.print_exc()
            
except Exception as e:
    print(f"❌ ERROR initializing SerpAPI activities connector: {str(e)}")
    traceback.print_exc()

print()

# Test OpenAI
print("🤖 Step 5: Testing OpenAI API...")
print("-" * 80)

try:
    from ai_implementation.openai_service import OpenAIService
    
    try:
        openai_service = OpenAIService()
        print("✅ OpenAI service initialized")
        
        # Test with a simple question
        print("Testing OpenAI with a simple question...")
        
        try:
            result = openai_service.answer_travel_question(
                "What is the capital of France?",
                context={"purpose": "API diagnostic test"}
            )
            
            if result and "Paris" in result:
                print("✅ OpenAI API is WORKING!")
                print(f"   Response preview: {result[:100]}...")
            else:
                print("⚠️  OpenAI responded but answer unexpected")
                print(f"   Response: {result[:200]}...")
                
        except Exception as e:
            print(f"❌ ERROR calling OpenAI API: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            print()
            print("   Possible issues:")
            print("   - Invalid API key")
            print("   - No API credits remaining")
            print("   - Rate limit exceeded")
            print("   - Network/connection issue")
            print("   - OpenAI service outage")
            
    except ValueError as e:
        print(f"❌ ERROR: {str(e)}")
        print("   OpenAI API key not configured!")
        
except Exception as e:
    print(f"❌ ERROR initializing OpenAI service: {str(e)}")
    traceback.print_exc()

print()

# Test OpenAI consolidation (the actual function used in production)
print("🔗 Step 6: Testing OpenAI Consolidation (Production Function)...")
print("-" * 80)

try:
    from ai_implementation.openai_service import OpenAIService
    
    try:
        openai_service = OpenAIService()
        
        # Create mock data similar to what would be passed in production
        mock_flights = [
            {
                "id": "TEST-FL-1",
                "price": 350,
                "airline": "American Airlines",
                "departure_time": "2024-12-01T10:00:00",
                "arrival_time": "2024-12-01T15:00:00",
                "duration": "5h 0m",
                "stops": 0
            }
        ]
        
        mock_hotels = [
            {
                "id": "TEST-HT-1",
                "name": "Test Hotel",
                "price_per_night": 150,
                "rating": 4.5
            }
        ]
        
        mock_activities = [
            {
                "id": "TEST-ACT-1",
                "name": "Test Activity",
                "price": 50,
                "category": "culture"
            }
        ]
        
        mock_preferences = {
            "budget_max": 2000,
            "adults": 2
        }
        
        print("Testing consolidate_travel_results function...")
        
        try:
            consolidated = openai_service.consolidate_travel_results(
                flight_results=mock_flights,
                hotel_results=mock_hotels,
                activity_results=mock_activities,
                user_preferences=mock_preferences
            )
            
            if consolidated and "error" not in consolidated:
                print("✅ OpenAI consolidation is WORKING!")
                print(f"   Summary: {consolidated.get('summary', 'N/A')[:100]}...")
            else:
                print("⚠️  OpenAI consolidation returned an error")
                print(f"   Response: {consolidated}")
                
        except Exception as e:
            print(f"❌ ERROR during consolidation: {str(e)}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            
    except ValueError as e:
        print(f"❌ ERROR: {str(e)}")
        
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
    traceback.print_exc()

print()

# Summary
print("=" * 80)
print("📊 DIAGNOSTIC SUMMARY")
print("=" * 80)
print()

# Check what's actually configured
issues = []

if not serpapi_key and not settings_serpapi:
    issues.append("❌ SerpAPI key is NOT configured (will use mock data)")

if not openai_key and not settings_openai:
    issues.append("❌ OpenAI key is NOT configured (AI features won't work)")

if serpapi_key and not settings_serpapi:
    issues.append("⚠️  SerpAPI key in environment but not in Django settings")

if openai_key and not settings_openai:
    issues.append("⚠️  OpenAI key in environment but not in Django settings")

if issues:
    print("ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("RECOMMENDATIONS:")
    print()
    print("1. For Render.com deployment:")
    print("   - Go to your Render dashboard")
    print("   - Navigate to your service → Environment")
    print("   - Add environment variables:")
    print("     * SERP_API_KEY=your-serpapi-key")
    print("     * OPENAI_API_KEY=your-openai-key")
    print()
    print("2. Verify API keys are valid:")
    print("   - SerpAPI: Check https://serpapi.com/dashboard")
    print("   - OpenAI: Check https://platform.openai.com/api-keys")
    print()
    print("3. Check API credits/quotas:")
    print("   - SerpAPI: Free tier = 100 searches/month")
    print("   - OpenAI: Check usage at https://platform.openai.com/usage")
    print()
else:
    print("✅ All API keys appear to be configured!")
    print()
    print("If APIs are still not working:")
    print("1. Check API credits/quotas")
    print("2. Verify keys are correct (not expired/revoked)")
    print("3. Check network connectivity from production server")
    print("4. Review production logs for detailed error messages")

print("=" * 80)
print("Diagnostic complete!")
print("=" * 80)


