"""
Views for AI Implementation
Handles travel search requests, API calls, and consolidated result display.
"""

import json
import gc  # For garbage collection to free memory
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction, models
from django.utils import timezone
from datetime import datetime

from .models import (
    TravelSearch,
    ConsolidatedResult,
    FlightResult,
    HotelResult,
    ActivityResult,
    GroupConsensus,
    AIGeneratedItinerary,
    SearchHistory,
    GroupItineraryOption,
    ItineraryVote,
)
from .forms import (
    TravelSearchForm,
    QuickSearchForm,
    GroupConsensusForm,
    ItineraryFeedbackForm,
    SaveItineraryForm,
    RefineSearchForm,
)
from .openai_service import OpenAIService
from .api_connectors import TravelAPIAggregator
from .serpapi_connector import SerpApiFlightsConnector, SerpApiActivitiesConnector
from .makcorps_connector import MakcorpsHotelConnector

from travel_groups.models import TravelGroup, GroupMember, TripPreference
from .airport_data import search_airports


def _generate_options_manually(
    member_prefs, flight_results, hotel_results, activity_results, search, group
):
    """
    Generate up to three voting options manually without OpenAI.
    Creates budget tiers (budget, balanced, premium) using unique flight/hotel pairings.
    Validates that destinations match member preferences and that flights/hotels align with them.
    """
    # Extract destinations from member preferences
    preference_destinations = []
    for pref in member_prefs:
        dest = pref.get("destination", "")
        if dest:
            preference_destinations.append(dest)

    print(f"[VALIDATION] Member preference destinations: {preference_destinations}")

    # Group flights and hotels by destination
    flights_by_dest = {}
    hotels_by_dest = {}

    for flight in flight_results:
        dest = flight.get("searched_destination", "")
        if dest:
            if dest not in flights_by_dest:
                flights_by_dest[dest] = []
            flights_by_dest[dest].append(flight)

    for hotel in hotel_results:
        dest = hotel.get("searched_destination", "")
        if dest:
            if dest not in hotels_by_dest:
                hotels_by_dest[dest] = []
            hotels_by_dest[dest].append(hotel)

    # Sort flights and hotels by price within each destination
    for dest in flights_by_dest:
        flights_by_dest[dest].sort(key=lambda x: float(x.get("price", 0) or 0))
    for dest in hotels_by_dest:
        hotels_by_dest[dest].sort(key=lambda x: float(x.get("price_per_night", 0) or 0))

    # Get unique destinations - prioritize destinations from member preferences
    all_available_destinations = list(
        set(list(flights_by_dest.keys()) + list(hotels_by_dest.keys()))
    )

    # Filter to only use destinations that match member preferences
    valid_destinations = []
    for pref_dest in preference_destinations:
        # Check if any available destination matches (case-insensitive, partial match)
        for avail_dest in all_available_destinations:
            if (
                pref_dest.lower() in avail_dest.lower()
                or avail_dest.lower() in pref_dest.lower()
            ):
                if avail_dest not in valid_destinations:
                    valid_destinations.append(avail_dest)
                    break

    # If no matches, use all available destinations
    if not valid_destinations:
        valid_destinations = all_available_destinations
        print(
            f"[WARNING] No destinations matched preferences. Using all available: {valid_destinations}"
        )
    else:
        print(
            f"[VALIDATION] Using destinations that match preferences: {valid_destinations}"
        )

    # Generate ALL possible combinations of flights + hotels by destination
    all_combinations = []
    used_combinations = set()  # Track (flight_id, hotel_id) pairs to avoid duplicates

    for dest in valid_destinations:
        flights = flights_by_dest.get(dest, [])
        hotels = hotels_by_dest.get(dest, [])

        if not flights or not hotels:
            continue

        # Generate combinations, ensuring uniqueness
        for flight in flights:
            for hotel in hotels:
                combo_key = (flight.get("id", ""), hotel.get("id", ""))
                if combo_key in used_combinations:
                    continue  # Skip duplicate combinations
                used_combinations.add(combo_key)

                flight_price = float(flight.get("price", 0) or 0)
                hotel_price = (
                    float(hotel.get("price_per_night", 0) or 0) * 7
                )  # Approximate for trip duration
                total_cost = flight_price + hotel_price

                all_combinations.append(
                    {
                        "destination": dest,
                        "flight": flight,
                        "hotel": hotel,
                        "total_cost": total_cost,
                        "flight_id": flight.get("id", ""),
                        "hotel_id": hotel.get("id", ""),
                    }
                )

    if not all_combinations:
        print("[ERROR] No valid flight+hotel combinations found!")
        return {
            "options": [],
            "voting_guidance": "No valid options could be generated.",
            "consensus_summary": "No valid options found.",
        }

    # Sort all combinations by total cost
    all_combinations.sort(key=lambda x: x["total_cost"])

    print(
        f"[DEBUG] Generated {len(all_combinations)} unique combinations, sorted by cost"
    )

    # Select up to 3 distinct options (A, B, C) spread across the price range
    selected_combinations = []
    target_count = min(3, len(all_combinations))

    if len(all_combinations) >= 3:
        selected_combinations = [
            all_combinations[0],
            all_combinations[len(all_combinations) // 2],
            all_combinations[-1],
        ]
    else:
        selected_combinations = all_combinations[:target_count]

    # Ensure selected_combinations have unique flight+hotel pairs
    unique_selected = []
    used_pairs = set()
    for combo in selected_combinations:
        pair_key = (combo["flight_id"], combo["hotel_id"])
        if pair_key not in used_pairs:
            used_pairs.add(pair_key)
            unique_selected.append(combo)

    # Fill remaining slots if needed
    idx = 0
    while len(unique_selected) < target_count and idx < len(all_combinations):
        combo = all_combinations[idx]
        pair_key = (combo["flight_id"], combo["hotel_id"])
        if pair_key not in used_pairs:
            used_pairs.add(pair_key)
            unique_selected.append(combo)
        idx += 1

    # Sort the final selected combinations by cost to ensure proper ordering
    unique_selected.sort(key=lambda x: x["total_cost"])

    # Create option objects
    options = []
    tier_names = [
        "Budget-Friendly",
        "Economy",
        "Balanced",
        "Comfort",
        "Premium",
        "Luxury",
        "Ultra-Premium",
        "Exclusive",
    ]
    tier_descriptions = [
        "Affordable option with economical flight and hotel choices.",
        "Economy option with budget-friendly choices.",
        "Mid-range option with good value flight and hotel choices.",
        "Comfort option with quality accommodations.",
        "Premium option with high-quality flight and hotel choices.",
        "Luxury option with top-tier accommodations.",
        "Ultra-premium option with exceptional quality.",
        "Exclusive option with the finest accommodations.",
    ]

    for idx, combo in enumerate(unique_selected[:target_count]):
        dest = combo["destination"]
        flight = combo["flight"]
        hotel = combo["hotel"]

        # Validate destinations match
        if flight.get("searched_destination", "") != dest:
            print(
                f"[VALIDATION ERROR] Flight destination mismatch: {flight.get('searched_destination')} != {dest}"
            )
        if hotel.get("searched_destination", "") != dest:
            print(
                f"[VALIDATION ERROR] Hotel destination mismatch: {hotel.get('searched_destination')} != {dest}"
            )

        option_letter = chr(65 + idx)  # A, B, or C

        options.append(
            {
                "option_letter": option_letter,
                "title": f"{tier_names[idx]} Trip to {dest}",
                "description": f"{tier_descriptions[idx]}",
                "selected_flight_id": flight.get("id", ""),
                "selected_hotel_id": hotel.get("id", ""),
                "selected_activity_ids": [],
                "estimated_total_cost": combo["total_cost"],
                "cost_per_person": (
                    combo["total_cost"] / group.member_count
                    if group.member_count > 0
                    else combo["total_cost"]
                ),
                "ai_reasoning": f"{tier_names[idx]} option selected for {dest}.",
                "compromise_explanation": f"This option represents the {tier_names[idx].lower()} tier of available options.",
                "intended_destination": dest,
            }
        )

    if len(options) >= 3:
        print(
            f"[SORTING] Final options sorted by cost: A=${options[0]['estimated_total_cost']:.2f}, B=${options[1]['estimated_total_cost']:.2f}, C=${options[2]['estimated_total_cost']:.2f}"
        )
    elif len(options) == 2:
        print(
            f"[SORTING] Final options sorted by cost: A=${options[0]['estimated_total_cost']:.2f}, B=${options[1]['estimated_total_cost']:.2f}"
        )
    elif len(options) == 1:
        print(
            f"[SORTING] Final options sorted by cost: A=${options[0]['estimated_total_cost']:.2f}"
        )
    else:
        print(f"[SORTING] No options generated")

    return {
        "options": options,
        "voting_guidance": "Review each option carefully. Option A is budget-friendly, Option B is balanced, and Option C is premium.",
        "consensus_summary": f"Generated {len(options)} unique options based on available flights and hotels, sorted by cost.",
    }


@login_required
def search_home(request):
    """Landing page for AI-powered travel search"""
    quick_form = QuickSearchForm()
    recent_searches = TravelSearch.objects.filter(user=request.user)[:5]

    context = {
        "quick_form": quick_form,
        "recent_searches": recent_searches,
    }
    return render(request, "ai_implementation/search_home.html", context)


@login_required
def advanced_search(request):
    """Advanced search page with more options"""
    if request.method == "POST":
        form = TravelSearchForm(request.POST)
        if form.is_valid():
            # Create travel search
            search = form.save(commit=False)
            search.user = request.user
            if not search.rooms:
                search.rooms = 1

            # Check if search is for a group
            group_id = request.POST.get("group_id")
            if group_id:
                try:
                    group = TravelGroup.objects.get(id=group_id)
                    # Verify user is a member
                    if GroupMember.objects.filter(
                        group=group, user=request.user
                    ).exists():
                        search.group = group
                except TravelGroup.DoesNotExist:
                    pass

            search.save()

            # Redirect to results page
            return redirect("ai_implementation:search_results", search_id=search.id)
    else:
        # Pre-fill from group preferences if group_id is provided
        group_id = request.GET.get("group_id")
        initial_data = {}

        if group_id:
            try:
                group = TravelGroup.objects.get(id=group_id)
                # Try to get consensus or use first member's preferences
                trip_prefs = TripPreference.objects.filter(group=group).first()
                if trip_prefs:
                    initial_data = {
                        "destination": trip_prefs.destination,
                        "start_date": trip_prefs.start_date,
                        "end_date": trip_prefs.end_date,
                        "adults": group.member_count,
                    }
            except TravelGroup.DoesNotExist:
                pass

        form = TravelSearchForm(initial=initial_data)

    # Get user's groups for dropdown
    user_groups = GroupMember.objects.filter(user=request.user).select_related("group")

    context = {
        "form": form,
        "user_groups": user_groups,
    }
    return render(request, "ai_implementation/advanced_search.html", context)


@login_required
def search_results(request, search_id):
    """Display consolidated search results with AI recommendations"""
    search = get_object_or_404(TravelSearch, id=search_id, user=request.user)

    # Check if results already exist
    try:
        consolidated = ConsolidatedResult.objects.get(search=search)
        flights = FlightResult.objects.filter(search=search)
        hotels = HotelResult.objects.filter(search=search)
        activities = ActivityResult.objects.filter(search=search)

        # Results already exist
        results_exist = True
    except ConsolidatedResult.DoesNotExist:
        # Need to perform search
        results_exist = False
        consolidated = None
        flights = []
        hotels = []
        activities = []

    # Allow explicit refresh to trigger new search run
    if request.GET.get("refresh") == "true":
        return redirect("ai_implementation:perform_search", search_id=search.id)

    # Parse consolidated results
    summary = consolidated.summary if consolidated else ""
    budget_analysis = (
        json.loads(consolidated.budget_analysis)
        if consolidated and consolidated.budget_analysis
        else {}
    )
    itinerary_suggestions = (
        json.loads(consolidated.itinerary_suggestions)
        if consolidated and consolidated.itinerary_suggestions
        else []
    )
    warnings = (
        json.loads(consolidated.warnings)
        if consolidated and consolidated.warnings
        else []
    )

    # Apply filters if provided
    refine_form = RefineSearchForm(request.GET)
    if refine_form.is_valid():
        max_price = refine_form.cleaned_data.get("max_price")
        min_rating = refine_form.cleaned_data.get("min_rating")
        sort_by = refine_form.cleaned_data.get("sort_by")

        # Filter hotels
        if max_price:
            hotels = hotels.filter(total_price__lte=max_price)
        if min_rating:
            hotels = hotels.filter(rating__gte=min_rating)

        # Sort
        if sort_by == "price_low":
            hotels = hotels.order_by("total_price")
            flights = flights.order_by("price")
        elif sort_by == "price_high":
            hotels = hotels.order_by("-total_price")
            flights = flights.order_by("-price")
        elif sort_by == "rating":
            hotels = hotels.order_by("-rating")
            activities = activities.order_by("-rating")

    # Create search history entry
    SearchHistory.objects.get_or_create(
        user=request.user, search=search, defaults={"viewed_results": True}
    )

    context = {
        "search": search,
        "consolidated": consolidated,
        "flights": flights[:10],  # Limit to top 10
        "hotels": hotels[:10],
        "activities": activities[:10],
        "summary": summary,
        "budget_analysis": budget_analysis,
        "itinerary_suggestions": itinerary_suggestions,
        "warnings": warnings,
        "refine_form": refine_form,
        "needs_results": not results_exist,
    }
    return render(request, "ai_implementation/search_results.html", context)


@login_required
@require_http_methods(["POST", "GET"])
def perform_search(request, search_id):
    """Perform the actual API searches and AI consolidation"""
    search = get_object_or_404(TravelSearch, id=search_id, user=request.user)

    if request.method == "GET":
        # Show loading page
        return render(request, "ai_implementation/searching.html", {"search": search})

    try:
        # Initialize SerpAPI for flights and activities, Makcorps for hotels
        serpapi_flights = SerpApiFlightsConnector()
        api_errors = []

        origin_location = (search.origin or "Denver").strip() or "Denver"
        if not search.origin:
            search.origin = origin_location
            search.save(update_fields=["origin"])

        # Prepare preferences
        preferences = {
            "budget_min": float(search.budget_min) if search.budget_min else None,
            "budget_max": float(search.budget_max) if search.budget_max else None,
            "accommodation_type": search.accommodation_type,
            "activity_preferences": (
                search.activity_categories.split(",")
                if search.activity_categories
                else []
            ),
            "adults": search.adults,
            "rooms": search.rooms,
        }

        # Search flights using SerpAPI
        flight_results = []
        try:
            print(
                f"Searching flights using SerpAPI: {origin_location} -> {search.destination}"
            )
            flight_results = serpapi_flights.search_flights(
                origin=origin_location,
                destination=search.destination,
                departure_date=search.start_date.strftime("%Y-%m-%d"),
                return_date=search.end_date.strftime("%Y-%m-%d"),
                adults=search.adults,
                max_results=50,
            )
            print(f"Found {len(flight_results)} flights from SerpAPI")
        except Exception as e:
            print(f"Error searching flights with SerpAPI: {str(e)}")
            api_errors.append(str(e))
            flight_results = []

        # Search hotels using Makcorps
        makcorps_hotels = MakcorpsHotelConnector()
        hotel_results = []
        try:
            print(f"Searching hotels using Makcorps: {search.destination}")
            hotel_results = makcorps_hotels.search_hotels(
                location=search.destination,
                check_in=search.start_date.strftime("%Y-%m-%d"),
                check_out=search.end_date.strftime("%Y-%m-%d"),
                adults=search.adults,
                rooms=search.rooms,
                max_results=50,
            )
            print(f"Found {len(hotel_results)} hotels from Makcorps")
        except Exception as e:
            print(f"Error searching hotels with Makcorps: {str(e)}")
            api_errors.append(str(e))
            hotel_results = []

        # Search activities using SerpAPI
        serpapi_activities = SerpApiActivitiesConnector()
        activity_results = []
        try:
            print(f"Searching activities using SerpAPI: {search.destination}")
            activity_categories = None
            if preferences and "activity_preferences" in preferences:
                activity_categories = preferences["activity_preferences"]
                if isinstance(activity_categories, str):
                    # Try to parse as comma-separated or JSON
                    try:
                        cats = json.loads(activity_categories)
                        if isinstance(cats, list):
                            activity_categories = cats
                    except:
                        # Treat as comma-separated string
                        activity_categories = [
                            c.strip() for c in activity_categories.split(",")
                        ]

            activity_results = serpapi_activities.search_activities(
                destination=search.destination,
                start_date=search.start_date.strftime("%Y-%m-%d"),
                end_date=search.end_date.strftime("%Y-%m-%d"),
                categories=activity_categories,
                max_results=50,
            )
            print(f"Found {len(activity_results)} activities from SerpAPI")
        except Exception as e:
            print(f"Error searching activities with SerpAPI: {str(e)}")
            api_errors.append(str(e))
            activity_results = []

        # Combine results: use SerpAPI for flights and activities, Makcorps for hotels
        api_results = {
            "flights": flight_results,
            "hotels": hotel_results,
            "activities": activity_results,
            "errors": api_errors,
        }

        # Save raw results to database
        with transaction.atomic():
            # Delete old results if any
            if api_results["flights"]:
                FlightResult.objects.filter(search=search).delete()
            if api_results["hotels"]:
                HotelResult.objects.filter(search=search).delete()
            if api_results["activities"]:
                ActivityResult.objects.filter(search=search).delete()

            # Save flight results
            for flight_data in api_results["flights"]:
                # Handle departure_time - convert to timezone-aware if needed
                dep_time = flight_data.get("departure_time", search.start_date)
                if isinstance(dep_time, str):
                    try:
                        # Try to parse string datetime
                        dep_time = datetime.fromisoformat(
                            dep_time.replace("Z", "+00:00")
                        )
                    except:
                        # Fallback to search start date
                        dep_time = search.start_date
                if isinstance(dep_time, datetime):
                    if timezone.is_naive(dep_time):
                        dep_time = timezone.make_aware(dep_time)
                elif hasattr(dep_time, "date"):  # Date object
                    dep_time = timezone.make_aware(
                        datetime.combine(dep_time, datetime.min.time())
                    )
                else:
                    dep_time = timezone.make_aware(
                        datetime.combine(search.start_date, datetime.min.time())
                    )

                # Handle arrival_time - convert to timezone-aware if needed
                arr_time = flight_data.get("arrival_time", search.start_date)
                if isinstance(arr_time, str):
                    try:
                        # Try to parse string datetime
                        arr_time = datetime.fromisoformat(
                            arr_time.replace("Z", "+00:00")
                        )
                    except:
                        # Fallback to search start date
                        arr_time = search.start_date
                if isinstance(arr_time, datetime):
                    if timezone.is_naive(arr_time):
                        arr_time = timezone.make_aware(arr_time)
                elif hasattr(arr_time, "date"):  # Date object
                    arr_time = timezone.make_aware(
                        datetime.combine(arr_time, datetime.min.time())
                    )
                else:
                    arr_time = timezone.make_aware(
                        datetime.combine(search.start_date, datetime.min.time())
                    )

                FlightResult.objects.create(
                    search=search,
                    external_id=flight_data.get("id", "N/A"),
                    airline=flight_data.get("airline", "Unknown"),
                    price=flight_data.get("price", 0),
                    currency=flight_data.get("currency", "USD"),
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    duration=flight_data.get("duration", "N/A"),
                    stops=flight_data.get("stops", 0),
                    booking_class=flight_data.get("booking_class", "Economy"),
                    seats_available=str(flight_data.get("seats_available", "N/A")),
                    searched_destination=flight_data.get(
                        "searched_destination", search.destination
                    ),
                    is_mock=flight_data.get("is_mock", False),
                )

            # Save hotel results
            for hotel_data in api_results["hotels"]:
                HotelResult.objects.create(
                    search=search,
                    external_id=hotel_data.get("id", "N/A"),
                    name=hotel_data.get("name", "Unknown Hotel"),
                    address=hotel_data.get("address", ""),
                    price_per_night=hotel_data.get("price_per_night", 0),
                    total_price=hotel_data.get("total_price", 0),
                    currency=hotel_data.get("currency", "USD"),
                    rating=hotel_data.get("rating"),
                    review_count=hotel_data.get("review_count", 0),
                    room_type=hotel_data.get("room_type", ""),
                    amenities=",".join(hotel_data.get("amenities", [])),
                    distance_from_center=hotel_data.get("distance_from_center", ""),
                    breakfast_included=hotel_data.get("breakfast_included", False),
                    cancellation_policy=hotel_data.get("cancellation_policy", ""),
                    searched_destination=hotel_data.get(
                        "searched_destination", search.destination
                    ),
                    is_mock=hotel_data.get("is_mock", False),
                )

            # Save activity results
            for activity_data in api_results["activities"]:
                ActivityResult.objects.create(
                    search=search,
                    external_id=activity_data.get("id", "N/A"),
                    name=activity_data.get("name", "Unknown Activity"),
                    category=activity_data.get("category", ""),
                    description=activity_data.get("description", ""),
                    price=activity_data.get("price", 0),
                    currency=activity_data.get("currency", "USD"),
                    duration_hours=activity_data.get("duration_hours", 2),
                    rating=activity_data.get("rating"),
                    review_count=activity_data.get("review_count", 0),
                    included=activity_data.get("included", ""),
                    meeting_point=activity_data.get("meeting_point", ""),
                    max_group_size=activity_data.get("max_group_size"),
                    languages=(
                        ",".join(activity_data.get("languages", []))
                        if isinstance(activity_data.get("languages"), list)
                        else activity_data.get("languages", "")
                    ),
                    cancellation_policy=activity_data.get("cancellation_policy", ""),
                    searched_destination=activity_data.get(
                        "searched_destination", search.destination
                    ),
                    is_mock=activity_data.get("is_mock", False),
                )

        # Use OpenAI to consolidate results
        try:
            openai_service = OpenAIService()
            consolidated_data = openai_service.consolidate_travel_results(
                flight_results=api_results["flights"],
                hotel_results=api_results["hotels"],
                activity_results=api_results["activities"],
                user_preferences=preferences,
            )

            # Update results with AI scores
            if "recommended_flights" in consolidated_data:
                for rec in consolidated_data["recommended_flights"]:
                    flight_id = rec.get("flight_id")
                    FlightResult.objects.filter(
                        search=search, external_id=flight_id
                    ).update(
                        ai_score=rec.get("score", 0), ai_reason=rec.get("reason", "")
                    )

            if "recommended_hotels" in consolidated_data:
                for rec in consolidated_data["recommended_hotels"]:
                    hotel_id = rec.get("hotel_id")
                    HotelResult.objects.filter(
                        search=search, external_id=hotel_id
                    ).update(
                        ai_score=rec.get("score", 0), ai_reason=rec.get("reason", "")
                    )

            if "recommended_activities" in consolidated_data:
                for rec in consolidated_data["recommended_activities"]:
                    activity_id = rec.get("activity_id")
                    ActivityResult.objects.filter(
                        search=search, external_id=activity_id
                    ).update(
                        ai_score=rec.get("score", 0), ai_reason=rec.get("reason", "")
                    )

            # Save consolidated result
            ConsolidatedResult.objects.update_or_create(
                search=search,
                defaults={
                    "summary": consolidated_data.get("summary", ""),
                    "budget_analysis": json.dumps(
                        consolidated_data.get("budget_analysis", {})
                    ),
                    "itinerary_suggestions": json.dumps(
                        consolidated_data.get("itinerary_suggestions", [])
                    ),
                    "warnings": json.dumps(consolidated_data.get("warnings", [])),
                    "recommended_flight_ids": json.dumps(
                        consolidated_data.get("recommended_flights", [])
                    ),
                    "recommended_hotel_ids": json.dumps(
                        consolidated_data.get("recommended_hotels", [])
                    ),
                    "recommended_activity_ids": json.dumps(
                        consolidated_data.get("recommended_activities", [])
                    ),
                    "raw_openai_response": json.dumps(consolidated_data),
                },
            )

        except Exception as e:
            print(f"Error with OpenAI consolidation: {str(e)}")
            messages.warning(
                request, "Search completed, but AI recommendations are unavailable."
            )

        # Mark search as completed
        search.is_completed = True
        search.save()

        return JsonResponse(
            {"success": True, "redirect_url": f"/ai/search/{search.id}/results/"}
        )

    except Exception as e:
        print(f"Error performing search: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def generate_group_consensus(request, group_id):
    """Generate AI consensus from group member preferences"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect("travel_groups:group_list")

    if request.method == "POST":
        form = GroupConsensusForm(request.POST)
        if form.is_valid():
            # Collect all member preferences
            trip_preferences = TripPreference.objects.filter(
                group=group, is_completed=True
            )

            if not trip_preferences.exists():
                messages.warning(
                    request,
                    "No member preferences found. Please ask members to submit their preferences first.",
                )
                return redirect("travel_groups:group_detail", group_id=group.id)

            # Prepare preferences data
            member_prefs = []
            for pref in trip_preferences:
                member_prefs.append(
                    {
                        "user": pref.user.username,
                        "destination": pref.destination,
                        "start_date": pref.start_date.strftime("%Y-%m-%d"),
                        "end_date": pref.end_date.strftime("%Y-%m-%d"),
                        "budget": pref.budget,
                        "travel_method": pref.travel_method,
                        "rental_car": pref.rental_car,
                        "accommodation_preference": pref.accommodation_preference,
                        "activity_preferences": pref.activity_preferences,
                        "dietary_restrictions": pref.dietary_restrictions,
                        "accessibility_needs": pref.accessibility_needs,
                        "notes": pref.additional_notes,
                    }
                )

            # Generate consensus using OpenAI
            try:
                openai_service = OpenAIService()
                consensus_data = openai_service.generate_group_consensus(member_prefs)

                # Save consensus
                GroupConsensus.objects.create(
                    group=group,
                    generated_by=request.user,
                    consensus_preferences=json.dumps(
                        consensus_data.get("consensus_preferences", {})
                    ),
                    compromise_areas=json.dumps(
                        consensus_data.get("compromise_areas", [])
                    ),
                    unanimous_preferences=json.dumps(
                        consensus_data.get("unanimous_preferences", [])
                    ),
                    conflicting_preferences=json.dumps(
                        consensus_data.get("conflicting_preferences", [])
                    ),
                    group_dynamics_notes=consensus_data.get("group_dynamics_notes", ""),
                    raw_openai_response=json.dumps(consensus_data),
                )

                messages.success(request, "Group consensus generated successfully!")
                return redirect(
                    "ai_implementation:view_group_consensus", group_id=group.id
                )

            except Exception as e:
                messages.error(request, f"Error generating consensus: {str(e)}")
                return redirect("travel_groups:group_detail", group_id=group.id)
    else:
        form = GroupConsensusForm()

    # Get member count and preferences count
    members_count = GroupMember.objects.filter(group=group).count()
    prefs_count = TripPreference.objects.filter(group=group, is_completed=True).count()

    context = {
        "group": group,
        "form": form,
        "members_count": members_count,
        "prefs_count": prefs_count,
    }
    return render(request, "ai_implementation/generate_consensus.html", context)


@login_required
def view_group_consensus(request, group_id):
    """View the AI-generated group consensus"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect("travel_groups:group_list")

    # Get the latest consensus
    consensus = GroupConsensus.objects.filter(group=group, is_active=True).first()

    if not consensus:
        messages.warning(request, "No consensus has been generated yet.")
        return redirect("ai_implementation:generate_group_consensus", group_id=group.id)

    # Parse JSON data
    consensus_prefs = json.loads(consensus.consensus_preferences)
    compromise_areas = (
        json.loads(consensus.compromise_areas) if consensus.compromise_areas else []
    )
    unanimous_prefs = (
        json.loads(consensus.unanimous_preferences)
        if consensus.unanimous_preferences
        else []
    )
    conflicting_prefs = (
        json.loads(consensus.conflicting_preferences)
        if consensus.conflicting_preferences
        else []
    )

    context = {
        "group": group,
        "consensus": consensus,
        "consensus_prefs": consensus_prefs,
        "compromise_areas": compromise_areas,
        "unanimous_prefs": unanimous_prefs,
        "conflicting_prefs": conflicting_prefs,
    }
    return render(request, "ai_implementation/view_consensus.html", context)


@login_required
@require_http_methods(["POST"])
def save_itinerary(request, search_id):
    """Save an AI-generated itinerary"""
    search = get_object_or_404(TravelSearch, id=search_id, user=request.user)

    form = SaveItineraryForm(request.POST)
    if form.is_valid():
        title = form.cleaned_data["title"]

        # Get selected options from form
        flight_id = request.POST.get("selected_flight")
        hotel_id = request.POST.get("selected_hotel")
        activity_ids = request.POST.getlist("selected_activities")

        # Calculate total cost
        total_cost = 0
        selected_flight = None
        selected_hotel = None

        if flight_id:
            selected_flight = FlightResult.objects.filter(id=flight_id).first()
            if selected_flight:
                total_cost += float(selected_flight.price)

        if hotel_id:
            selected_hotel = HotelResult.objects.filter(id=hotel_id).first()
            if selected_hotel:
                total_cost += float(selected_hotel.total_price)

        for activity_id in activity_ids:
            activity = ActivityResult.objects.filter(id=activity_id).first()
            if activity:
                total_cost += float(activity.price)

        # Generate description using OpenAI
        try:
            openai_service = OpenAIService()
            activity_names = [
                ActivityResult.objects.get(id=aid).name for aid in activity_ids
            ]
            duration_days = (search.end_date - search.start_date).days

            description = openai_service.create_itinerary_description(
                destination=search.destination,
                activities=activity_names,
                duration_days=duration_days,
                preferences={"budget": total_cost},
            )
        except:
            description = f"Trip to {search.destination} from {search.start_date} to {search.end_date}"

        # Create itinerary
        itinerary = AIGeneratedItinerary.objects.create(
            user=request.user,
            search=search,
            title=title,
            destination=search.destination,
            description=description,
            duration_days=(search.end_date - search.start_date).days,
            selected_flight=selected_flight,
            selected_hotel=selected_hotel,
            selected_activities=json.dumps(activity_ids),
            estimated_total_cost=total_cost,
            is_saved=True,
        )

        # Update search history
        SearchHistory.objects.filter(user=request.user, search=search).update(
            saved_itinerary=True
        )

        messages.success(request, "Itinerary saved successfully!")
        return JsonResponse({"success": True, "itinerary_id": str(itinerary.id)})

    return JsonResponse({"success": False, "errors": form.errors})


@login_required
def my_itineraries(request):
    """View user's saved AI-generated itineraries"""
    itineraries = AIGeneratedItinerary.objects.filter(user=request.user, is_saved=True)

    context = {
        "itineraries": itineraries,
    }
    return render(request, "ai_implementation/my_itineraries.html", context)


@login_required
def view_itinerary(request, itinerary_id):
    """View details of a saved itinerary"""
    itinerary = get_object_or_404(
        AIGeneratedItinerary, id=itinerary_id, user=request.user
    )

    # Parse selected activities
    activity_ids = (
        json.loads(itinerary.selected_activities)
        if itinerary.selected_activities
        else []
    )
    activities = ActivityResult.objects.filter(id__in=activity_ids)

    context = {
        "itinerary": itinerary,
        "activities": activities,
    }
    return render(request, "ai_implementation/view_itinerary.html", context)


@login_required
def airport_autocomplete(request):
    """Autocomplete endpoint for airport/city search"""
    query = request.GET.get("q", "").strip()

    if not query:
        return JsonResponse({"airports": []})

    airports = search_airports(query, limit=10)

    return JsonResponse(
        {
            "airports": [
                {
                    "code": a["code"],
                    "display": a["display"],
                    "full_display": a["full_display"],
                    "city": a["city"],
                    "country": a["country"],
                }
                for a in airports
            ]
        }
    )


def _convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: _convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_convert_decimals_to_float(item) for item in obj)
    else:
        return obj


def _generate_single_new_option(group, consensus, search, member_prefs):
    """Helper function to generate a single new itinerary option from existing search data"""
    from decimal import Decimal

    # Get existing search results
    flights = FlightResult.objects.filter(search=search)
    hotels = HotelResult.objects.filter(search=search)
    activities = ActivityResult.objects.filter(search=search)

    if not flights.exists() or not hotels.exists():
        return None

    # Prepare lightweight data for OpenAI
    lightweight_flights = []
    for flight in flights[:10]:
        lightweight_flights.append(
            {
                "id": flight.external_id,
                "price": float(flight.price),
                "searched_destination": flight.searched_destination
                or search.destination,
                "total_amount": float(flight.price),
                "owner": {},
            }
        )

    lightweight_hotels = []
    for hotel in hotels[:15]:
        lightweight_hotels.append(
            {
                "id": hotel.external_id,
                "name": hotel.name,
                "price_per_night": float(hotel.price_per_night),
                "rating": hotel.rating,
                "searched_destination": hotel.searched_destination
                or search.destination,
            }
        )

    lightweight_activities = []
    for activity in activities[:20]:
        lightweight_activities.append(
            {
                "id": activity.external_id,
                "name": activity.name,
                "price": float(activity.price),
                "category": activity.category,
                "searched_destination": activity.searched_destination
                or search.destination,
            }
        )

    # Convert all data to JSON-serializable format (convert Decimals to float)
    member_prefs_clean = _convert_decimals_to_float(member_prefs)
    lightweight_flights_clean = _convert_decimals_to_float(lightweight_flights)
    lightweight_hotels_clean = _convert_decimals_to_float(lightweight_hotels)
    lightweight_activities_clean = _convert_decimals_to_float(lightweight_activities)

    # Generate one option using OpenAI or manual fallback
    try:
        openai_service = OpenAIService()
        options_data = openai_service.generate_three_itinerary_options(
            member_preferences=member_prefs_clean,
            flight_results=lightweight_flights_clean,
            hotel_results=lightweight_hotels_clean,
            activity_results=lightweight_activities_clean,
            selected_dates={
                "start_date": search.start_date.strftime("%Y-%m-%d"),
                "end_date": search.end_date.strftime("%Y-%m-%d"),
                "duration_days": (search.end_date - search.start_date).days,
            },
        )
        # Take the first option from the generated options
        if options_data.get("options"):
            option_data = options_data["options"][0]  # Take first option
        else:
            return None
    except Exception as e:
        print(f"[WARNING] OpenAI not available for new option: {str(e)}")
        # Use manual generation
        manual_options = _generate_options_manually(
            member_prefs=member_prefs_clean,
            flight_results=lightweight_flights_clean,
            hotel_results=lightweight_hotels_clean,
            activity_results=lightweight_activities_clean,
            search=search,
            group=group,
        )
        if manual_options.get("options"):
            option_data = manual_options["options"][0]  # Take first option
        else:
            return None

    # Get intended destination
    intended_dest = option_data.get("intended_destination", "")
    if not intended_dest:
        title = option_data.get("title", "")
        if " to " in title:
            intended_dest = title.split(" to ")[-1].strip()

    # Find matching flight and hotel
    selected_flight = None
    flight_id = option_data.get("selected_flight_id")
    if flight_id:
        flight = FlightResult.objects.filter(
            search=search, external_id=flight_id
        ).first()
        if flight:
            selected_flight = flight

    selected_hotel = None
    hotel_id = option_data.get("selected_hotel_id")
    if hotel_id:
        hotel = HotelResult.objects.filter(search=search, external_id=hotel_id).first()
        if hotel:
            selected_hotel = hotel

    # Calculate costs
    total_cost = 0.0
    if selected_flight:
        total_cost += float(selected_flight.price)
    if selected_hotel:
        total_cost += float(selected_hotel.total_price)

    cost_per_person = (
        total_cost / group.member_count if group.member_count > 0 else total_cost
    )

    # Get next available option letter
    existing_letters = set(
        GroupItineraryOption.objects.filter(group=group).values_list(
            "option_letter", flat=True
        )
    )
    available_letters = [
        letter
        for letter, _ in GroupItineraryOption.OPTION_CHOICES
        if letter not in existing_letters
    ]
    if not available_letters:
        # If all letters used, use a random one
        option_letter = random.choice(
            [letter for letter, _ in GroupItineraryOption.OPTION_CHOICES]
        )
    else:
        option_letter = available_letters[0]

    # Create the new option
    new_option = GroupItineraryOption.objects.create(
        group=group,
        consensus=consensus,
        option_letter=option_letter,
        title=option_data["title"],
        description=option_data["description"],
        destination=intended_dest,
        search=search,
        selected_flight=selected_flight,
        selected_hotel=selected_hotel,
        selected_activities=json.dumps(option_data.get("selected_activity_ids", [])),
        estimated_total_cost=total_cost,
        cost_per_person=cost_per_person,
        ai_reasoning=option_data.get("ai_reasoning", ""),
        compromise_explanation=option_data.get("compromise_explanation", ""),
        status="active",
        display_order=(
            (
                GroupItineraryOption.objects.filter(group=group).aggregate(
                    max_order=models.Max("display_order")
                )["max_order"]
            )
            or 0
        )
        + 1,
    )

    return new_option


@login_required
@require_http_methods(["POST"])
def roll_again(request, group_id, option_id):
    """Handle 'Roll Again' - vote no and advance to next option"""
    group = get_object_or_404(TravelGroup, id=group_id)
    current_option = get_object_or_404(GroupItineraryOption, id=option_id, group=group)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not a group member"})

    # Check if user already voted on THIS OPTION - update or create their vote
    existing_vote = ItineraryVote.objects.filter(
        group=group, user=request.user, option=current_option
    ).first()

    # Create or update vote with "ROLL_AGAIN" marker in comment to indicate "no" vote
    if existing_vote:
        existing_vote.comment = "ROLL_AGAIN"
        existing_vote.save()
    else:
        # Check if user has a vote for a different option (shouldn't happen, but handle it)
        other_vote = ItineraryVote.objects.filter(
            group=group, user=request.user
        ).first()
        if other_vote:
            # Update existing vote to point to current option
            other_vote.option = current_option
            other_vote.comment = "ROLL_AGAIN"
            other_vote.save()
        else:
            # Create a new vote record marking "no"
            ItineraryVote.objects.create(
                option=current_option,
                user=request.user,
                group=group,
                comment="ROLL_AGAIN",  # Special marker for "no" vote
            )

    # Check how many members have voted on THIS OPTION (all votes, yes or no)
    total_members = GroupMember.objects.filter(group=group).count()
    votes_cast = ItineraryVote.objects.filter(
        group=group, option=current_option
    ).count()

    # Check if all members have voted on this option
    if votes_cast >= total_members:
        # Check if this option has unanimous "yes" votes (votes without ROLL_AGAIN comment)
        yes_votes = (
            ItineraryVote.objects.filter(group=group, option=current_option)
            .exclude(comment="ROLL_AGAIN")
            .count()
        )

        if yes_votes == total_members:
            # Unanimous yes - should not happen if someone clicked Roll Again, but handle it
            current_option.status = "accepted"
            current_option.is_winner = True
            current_option.save()
            return JsonResponse(
                {
                    "success": False,
                    "error": "This option has unanimous approval and should be accepted",
                }
            )
        else:
            # Not unanimous - reject and load next pending option
            current_option.status = "rejected"
            current_option.save()

            # Clear all votes for the rejected option (so members can vote on next option)
            ItineraryVote.objects.filter(group=group, option=current_option).delete()

            # Get next pending option (already generated and stored)
            pending_options = list(
                GroupItineraryOption.objects.filter(
                    group=group, status="pending"
                ).order_by("display_order", "option_letter")
            )

            if pending_options:
                # Activate the first pending option
                next_option = pending_options[0]
                next_option.status = "active"

                # Set display order (increment from highest existing)
                max_order = (
                    GroupItineraryOption.objects.filter(group=group).aggregate(
                        max_order=models.Max("display_order")
                    )["max_order"]
                    or 0
                )
                next_option.display_order = max_order + 1
                next_option.save()

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Rolled again! Now showing Option {next_option.option_letter}",
                        "next_option_id": str(next_option.id),
                        "next_option_letter": next_option.option_letter,
                        "remaining_pending": len(pending_options) - 1,
                        "advanced": True,
                    }
                )
            else:
                # No more pending options - try to generate a new one
                search = current_option.search
                consensus = current_option.consensus

                # Get member preferences for generating new option
                trip_preferences = TripPreference.objects.filter(
                    group=group, is_completed=True
                )
                member_prefs = []
                for pref in trip_preferences:
                    member_prefs.append(
                        {
                            "user": pref.user.username,
                            "destination": pref.destination,
                            "start_date": pref.start_date.strftime("%Y-%m-%d"),
                            "end_date": pref.end_date.strftime("%Y-%m-%d"),
                            "budget": str(pref.budget),
                            "travel_method": pref.travel_method,
                            "rental_car": pref.rental_car,
                            "accommodation_preference": pref.accommodation_preference
                            or "",
                            "activity_preferences": pref.activity_preferences or "",
                            "dietary_restrictions": pref.dietary_restrictions or "",
                            "accessibility_needs": pref.accessibility_needs or "",
                            "notes": pref.additional_notes or "",
                        }
                    )

                # Generate a new option
                next_option = _generate_single_new_option(
                    group, consensus, search, member_prefs
                )

                if not next_option:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "No more options available. Please generate new trip options.",
                        }
                    )

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Rolled again! Generated new Option {next_option.option_letter}",
                        "next_option_id": str(next_option.id),
                        "next_option_letter": next_option.option_letter,
                        "advanced": True,
                    }
                )
    else:
        # Not everyone has voted yet - just record the "no" vote
        return JsonResponse(
            {
                "success": True,
                "message": "Your 'Roll Again' vote has been recorded. Waiting for other members to vote...",
                "waiting": True,
                "votes_cast": votes_cast,
                "total_members": total_members,
            }
        )


@login_required
@require_http_methods(["POST"])
def advance_to_next_option(request, group_id):
    """Advance to the next pending option when current one is rejected"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not a group member"})

    # Get current active option
    current_active = GroupItineraryOption.objects.filter(
        group=group, status="active"
    ).first()

    if not current_active:
        return JsonResponse({"success": False, "error": "No active option found"})

    # Check if all members have voted on the current active option (required before advancing)
    total_members = GroupMember.objects.filter(group=group).count()
    votes_cast = ItineraryVote.objects.filter(
        group=group, option=current_active
    ).count()

    if votes_cast < total_members:
        return JsonResponse(
            {
                "success": False,
                "error": "All members must vote on the current option before advancing to next option",
            }
        )

    # Check if current option is unanimous
    yes_votes_for_active = (
        ItineraryVote.objects.filter(group=group, option=current_active)
        .exclude(comment="ROLL_AGAIN")
        .count()
    )
    if yes_votes_for_active == total_members:
        # Unanimous - should not advance, option should be accepted
        return JsonResponse(
            {
                "success": False,
                "error": "Current option has unanimous vote and should be accepted",
            }
        )

    # Mark current option as rejected
    current_active.status = "rejected"
    current_active.save()

    # Clear all votes for the rejected option (so members can vote on next option)
    ItineraryVote.objects.filter(group=group, option=current_active).delete()

    # Get next pending option randomly
    pending_options = list(
        GroupItineraryOption.objects.filter(group=group, status="pending")
    )

    if not pending_options:
        return JsonResponse(
            {"success": False, "error": "No more pending options available"}
        )

    # Randomly select next option using module-level random import
    next_option = random.choice(pending_options)
    next_option.status = "active"

    # Set display order (increment from highest existing)
    max_order = (
        GroupItineraryOption.objects.filter(group=group).aggregate(
            max_order=models.Max("display_order")
        )["max_order"]
        or 0
    )
    next_option.display_order = max_order + 1
    next_option.save()

    return JsonResponse(
        {
            "success": True,
            "message": f"Advanced to Option {next_option.option_letter}",
            "next_option_id": str(next_option.id),
            "next_option_letter": next_option.option_letter,
            "remaining_pending": len(pending_options) - 1,
        }
    )


@login_required
def generate_voting_options(request, group_id):
    """Generate 3 itinerary options for group voting based on member preferences"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect("travel_groups:group_list")

    if request.method == "POST":
        # Get dates from request body (from date picker modal)
        import json as json_module
        from datetime import datetime

        try:
            body_data = json_module.loads(request.body) if request.body else {}
        except json_module.JSONDecodeError:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid JSON in request body",
                },
                status=400,
            )
        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Error parsing request data",
                },
                status=400,
            )

        # Get dates and origin from JSON body or use None as fallback
        selected_start_date = body_data.get("start_date")
        selected_end_date = body_data.get("end_date")
        selected_origin = body_data.get("origin", "").strip()

        # Collect all member preferences
        trip_preferences = TripPreference.objects.filter(group=group, is_completed=True)

        if trip_preferences.count() < 2:
            # Return JSON error for AJAX call
            return JsonResponse(
                {
                    "success": False,
                    "error": "Need at least 2 members with preferences to generate options.",
                },
                status=400,
            )

        # Prepare preferences data
        member_prefs = []
        for pref in trip_preferences:
            member_prefs.append(
                {
                    "user": pref.user.username,
                    "destination": pref.destination,
                    "start_date": pref.start_date.strftime("%Y-%m-%d"),
                    "end_date": pref.end_date.strftime("%Y-%m-%d"),
                    "budget": pref.budget,
                    "travel_method": pref.travel_method,
                    "rental_car": pref.rental_car,
                    "accommodation_preference": pref.accommodation_preference,
                    "activity_preferences": pref.activity_preferences,
                    "dietary_restrictions": pref.dietary_restrictions,
                    "accessibility_needs": pref.accessibility_needs,
                    "notes": pref.additional_notes,
                }
            )

        # Extract all unique destinations from member preferences
        destinations = set()
        for pref in trip_preferences:
            if pref.destination:
                destinations.add(pref.destination.strip())

        destinations_list = list(destinations)
        print(
            f"[*] Found {len(destinations_list)} unique destinations from members: {destinations_list}"
        )

        # Use first preference as base for dates
        first_pref = trip_preferences.first()

        # Use selected dates if provided, otherwise use first preference dates
        if selected_start_date and selected_end_date:
            search_start_date = datetime.strptime(
                selected_start_date, "%Y-%m-%d"
            ).date()
            search_end_date = datetime.strptime(selected_end_date, "%Y-%m-%d").date()
            print(f"[*] Using selected dates: {search_start_date} to {search_end_date}")
        else:
            search_start_date = first_pref.start_date
            search_end_date = first_pref.end_date
            print(
                f"[*] Using preference dates: {search_start_date} to {search_end_date}"
            )

        try:
            # Create a search for the group with all destinations combined
            combined_destination = ", ".join(destinations_list)
            search = TravelSearch.objects.create(
                user=request.user,
                group=group,
                destination=combined_destination,
                start_date=search_start_date,
                end_date=search_end_date,
                adults=group.member_count,
                rooms=max(1, group.member_count // 2),  # Estimate rooms
            )

            # Search for travel options for EACH destination
            serpapi_flights = SerpApiFlightsConnector()
            serpapi_activities = SerpApiActivitiesConnector()

            # Get origin from user input or use default
            if selected_origin:
                # Extract airport code if it's in the format "CODE - City, Country" or just use the value
                origin_location = selected_origin
                # If it contains a dash, try to extract the code (format: "DEN - Denver, USA")
                if " - " in origin_location:
                    origin_location = origin_location.split(" - ")[0].strip()
                # If it's just a 3-letter code, use it directly
                elif len(origin_location) == 3 and origin_location.isupper():
                    origin_location = origin_location
                # Otherwise, try to find the airport code from the city name
                else:
                    # Search for airport by city name
                    airports = search_airports(origin_location, limit=1)
                    if airports:
                        origin_location = airports[0]["code"]
                    else:
                        # Fallback: use the input as-is (might be a city name)
                        origin_location = origin_location
                print(f"[*] Using selected origin: {origin_location}")
            else:
                # Default origin is Denver
                origin_location = "Denver"
                print(f"[*] Using default origin: {origin_location}")

            # Combine results from all destinations
            all_flights = []
            all_hotels = []
            all_activities = []

            for destination in destinations_list:
                print(f"\n[*] Searching for {destination}...")

                # Use SerpApi for flights
                try:
                    print(
                        f"  [FLIGHT] Searching flights using SerpApi: {origin_location} -> {destination}"
                    )
                    serpapi_flight_results = serpapi_flights.search_flights(
                        origin=origin_location,
                        destination=destination,
                        departure_date=search_start_date.strftime("%Y-%m-%d"),
                        return_date=search_end_date.strftime("%Y-%m-%d"),
                        adults=group.member_count,
                        max_results=10,
                    )

                    # Verify we got real flights (not mock)
                    if serpapi_flight_results:
                        mock_count = sum(
                            1 for f in serpapi_flight_results if f.get("is_mock", False)
                        )
                        if mock_count == len(serpapi_flight_results):
                            print(
                                f"  [ERROR] All {len(serpapi_flight_results)} flights are mock data - SerpApi did not return real flights"
                            )
                            raise Exception(
                                "SerpApi returned only mock data - API may be failing"
                            )
                        else:
                            real_count = len(serpapi_flight_results) - mock_count
                            print(
                                f"  [OK] Found {real_count} real flights and {mock_count} mock flights from SerpApi"
                            )

                    # Tag flights with destination
                    for flight in serpapi_flight_results:
                        # Skip mock flights - we only want real data
                        if not flight.get("is_mock", False):
                            flight["searched_destination"] = destination
                            all_flights.append(flight)
                        else:
                            print(
                                f"  [SKIP] Skipping mock flight: {flight.get('id', 'unknown')}"
                            )

                    print(
                        f"  [OK] Added {len([f for f in serpapi_flight_results if not f.get('is_mock', False)])} real flights to results"
                    )

                except Exception as e:
                    import traceback
                    from django.conf import settings

                    print(f"  [ERROR] Error with SerpApi for {destination}: {str(e)}")
                    # Only print full traceback in DEBUG mode to avoid exposing internal details
                    if settings.DEBUG:
                        print(traceback.format_exc())
                    else:
                        print(
                            f"  [ERROR] See server logs for full traceback (DEBUG mode disabled)"
                        )
                    # Don't continue with mock data - fail explicitly so user knows API is not working
                    print(
                        f"  [ERROR] Cannot proceed without real flight data for {destination}"
                    )
                    # Still continue to other destinations, but log the error

                # Use Makcorps for hotels
                makcorps_hotels = MakcorpsHotelConnector()
                try:
                    print(f"  [HOTEL] Searching hotels using Makcorps: {destination}")
                    hotel_results = makcorps_hotels.search_hotels(
                        location=destination,
                        check_in=search_start_date.strftime("%Y-%m-%d"),
                        check_out=search_end_date.strftime("%Y-%m-%d"),
                        adults=group.member_count,
                        rooms=search.rooms,
                        max_results=20,
                    )

                    # Tag hotels with destination
                    for hotel in hotel_results:
                        hotel["searched_destination"] = destination
                        all_hotels.append(hotel)

                    print(f"  [OK] Added {len(hotel_results)} hotels from Makcorps")
                except Exception as e:
                    print(f"  [ERROR] Error with Makcorps for {destination}: {str(e)}")
                    import traceback
                    from django.conf import settings

                    if settings.DEBUG:
                        print(traceback.format_exc())

                # Use SerpAPI for activities
                try:
                    print(
                        f"  [ACTIVITY] Searching activities using SerpAPI: {destination}"
                    )
                    # Get activity preferences from member preferences if available
                    activity_categories = []
                    for pref in trip_preferences:
                        if pref.activity_preferences:
                            if isinstance(pref.activity_preferences, str):
                                # Try to parse as comma-separated or JSON
                                try:
                                    cats = json.loads(pref.activity_preferences)
                                    if isinstance(cats, list):
                                        activity_categories.extend(cats)
                                except Exception:
                                    # Treat as comma-separated string
                                    activity_categories.extend(
                                        [
                                            c.strip()
                                            for c in pref.activity_preferences.split(
                                                ","
                                            )
                                        ]
                                    )
                            elif isinstance(pref.activity_preferences, list):
                                activity_categories.extend(pref.activity_preferences)

                    # Remove duplicates
                    activity_categories = list(set(activity_categories))[
                        :3
                    ]  # Limit to 3 categories

                    activity_results = serpapi_activities.search_activities(
                        destination=destination,
                        start_date=search_start_date.strftime("%Y-%m-%d"),
                        end_date=search_end_date.strftime("%Y-%m-%d"),
                        categories=activity_categories if activity_categories else None,
                        max_results=20,
                    )

                    # Tag activities with destination
                    for activity in activity_results:
                        activity["searched_destination"] = destination
                        all_activities.append(activity)

                    print(
                        f"  [OK] Added {len(activity_results)} activities from SerpAPI"
                    )
                except Exception as e:
                    print(
                        f"  [ERROR] Error with SerpAPI activities for {destination}: {str(e)}"
                    )
                    import traceback
                    from django.conf import settings

                    if settings.DEBUG:
                        print(traceback.format_exc())

            print(f"\n[OK] Combined Results:")
            print(
                f"   Flights: {len(all_flights)} from {len(destinations_list)} destinations"
            )
            print(
                f"   Hotels: {len(all_hotels)} from {len(destinations_list)} destinations"
            )
            print(
                f"   Activities: {len(all_activities)} from {len(destinations_list)} destinations"
            )

            # Show breakdown by destination
            if all_hotels:
                print(f"\n[INFO] Hotels by Destination:")
                dest_hotel_count = {}
                for hotel in all_hotels:
                    dest = hotel.get("searched_destination", "Unknown")
                    dest_hotel_count[dest] = dest_hotel_count.get(dest, 0) + 1
                for dest, count in dest_hotel_count.items():
                    print(f"   - {dest}: {count} hotels")

            # Use combined results
            api_results = {
                "flights": all_flights,
                "hotels": all_hotels,
                "activities": all_activities,
            }

            # Save results to database
            with transaction.atomic():
                # Save flight results
                for flight_data in api_results["flights"]:
                    # Handle departure_time - convert to timezone-aware if needed
                    dep_time = flight_data.get("departure_time", search.start_date)
                    if isinstance(dep_time, str):
                        try:
                            # Try to parse string datetime
                            dep_time = datetime.fromisoformat(
                                dep_time.replace("Z", "+00:00")
                            )
                        except:
                            # Fallback to search start date
                            dep_time = search.start_date
                    if isinstance(dep_time, datetime):
                        if timezone.is_naive(dep_time):
                            dep_time = timezone.make_aware(dep_time)
                    elif hasattr(dep_time, "date"):  # Date object
                        dep_time = timezone.make_aware(
                            datetime.combine(dep_time, datetime.min.time())
                        )
                    else:
                        dep_time = timezone.make_aware(
                            datetime.combine(search.start_date, datetime.min.time())
                        )

                    # Handle arrival_time - convert to timezone-aware if needed
                    arr_time = flight_data.get("arrival_time", search.start_date)
                    if isinstance(arr_time, str):
                        try:
                            # Try to parse string datetime
                            arr_time = datetime.fromisoformat(
                                arr_time.replace("Z", "+00:00")
                            )
                        except:
                            # Fallback to search start date
                            arr_time = search.start_date
                    if isinstance(arr_time, datetime):
                        if timezone.is_naive(arr_time):
                            arr_time = timezone.make_aware(arr_time)
                    elif hasattr(arr_time, "date"):  # Date object
                        arr_time = timezone.make_aware(
                            datetime.combine(arr_time, datetime.min.time())
                        )
                    else:
                        arr_time = timezone.make_aware(
                            datetime.combine(search.start_date, datetime.min.time())
                        )

                    FlightResult.objects.create(
                        search=search,
                        external_id=flight_data.get("id", "N/A"),
                        airline=flight_data.get("airline", "Unknown"),
                        price=flight_data.get("price", 0),
                        currency=flight_data.get("currency", "USD"),
                        departure_time=dep_time,
                        arrival_time=arr_time,
                        duration=flight_data.get("duration", "N/A"),
                        stops=flight_data.get("stops", 0),
                        booking_class=flight_data.get("booking_class", "Economy"),
                        seats_available=str(flight_data.get("seats_available", "N/A")),
                        searched_destination=flight_data.get(
                            "searched_destination", search.destination
                        ),
                        is_mock=flight_data.get("is_mock", False),
                    )

                # Save hotel results
                for hotel_data in api_results["hotels"]:
                    HotelResult.objects.create(
                        search=search,
                        external_id=hotel_data.get("id", "N/A"),
                        name=hotel_data.get("name", "Unknown Hotel"),
                        address=hotel_data.get("address", ""),
                        price_per_night=hotel_data.get("price_per_night", 0),
                        total_price=hotel_data.get("total_price", 0),
                        currency=hotel_data.get("currency", "USD"),
                        rating=hotel_data.get("rating"),
                        review_count=hotel_data.get("review_count", 0),
                        room_type=hotel_data.get("room_type", ""),
                        amenities=",".join(hotel_data.get("amenities", [])),
                        distance_from_center=hotel_data.get("distance_from_center", ""),
                        breakfast_included=hotel_data.get("breakfast_included", False),
                        cancellation_policy=hotel_data.get("cancellation_policy", ""),
                        searched_destination=hotel_data.get(
                            "searched_destination", search.destination
                        ),
                        is_mock=hotel_data.get("is_mock", False),
                    )

                # Save activity results
                for activity_data in api_results["activities"]:
                    ActivityResult.objects.create(
                        search=search,
                        external_id=activity_data.get("id", "N/A"),
                        name=activity_data.get("name", "Unknown Activity"),
                        category=activity_data.get("category", ""),
                        description=activity_data.get("description", ""),
                        price=activity_data.get("price", 0),
                        currency=activity_data.get("currency", "USD"),
                        duration_hours=activity_data.get("duration_hours", 2),
                        rating=activity_data.get("rating"),
                        review_count=activity_data.get("review_count", 0),
                        included=activity_data.get("included", ""),
                        meeting_point=activity_data.get("meeting_point", ""),
                        max_group_size=activity_data.get("max_group_size"),
                        languages=(
                            ",".join(activity_data.get("languages", []))
                            if isinstance(activity_data.get("languages"), list)
                            else activity_data.get("languages", "")
                        ),
                        cancellation_policy=activity_data.get(
                            "cancellation_policy", ""
                        ),
                        searched_destination=activity_data.get(
                            "searched_destination", search.destination
                        ),
                        is_mock=activity_data.get("is_mock", False),
                    )

            # Generate consensus first (or create basic consensus if OpenAI unavailable)
            try:
                openai_service = OpenAIService()
                consensus_data = openai_service.generate_group_consensus(member_prefs)
            except (ValueError, Exception) as e:
                # OpenAI API key not configured or error - create basic consensus
                print(f"[WARNING] OpenAI not available: {str(e)}")
                print("[INFO] Creating basic consensus without AI...")

                # Create basic consensus data from member preferences
                destinations = [
                    pref.get("destination", "")
                    for pref in member_prefs
                    if pref.get("destination")
                ]
                budgets = [
                    float(pref.get("budget", "0").replace("$", "").replace(",", ""))
                    for pref in member_prefs
                    if pref.get("budget")
                ]

                consensus_data = {
                    "consensus_preferences": {
                        "destinations": list(set(destinations)),
                        "average_budget": sum(budgets) / len(budgets) if budgets else 0,
                        "min_budget": min(budgets) if budgets else 0,
                        "max_budget": max(budgets) if budgets else 0,
                    },
                    "compromise_areas": [],
                    "unanimous_preferences": [],
                    "conflicting_preferences": [],
                    "group_dynamics_notes": "Generated without AI assistance - using basic preference analysis.",
                }

            # Save consensus
            consensus = GroupConsensus.objects.create(
                group=group,
                generated_by=request.user,
                consensus_preferences=json.dumps(
                    consensus_data.get("consensus_preferences", {})
                ),
                compromise_areas=json.dumps(consensus_data.get("compromise_areas", [])),
                unanimous_preferences=json.dumps(
                    consensus_data.get("unanimous_preferences", [])
                ),
                conflicting_preferences=json.dumps(
                    consensus_data.get("conflicting_preferences", [])
                ),
                group_dynamics_notes=consensus_data.get("group_dynamics_notes", ""),
                raw_openai_response=json.dumps(consensus_data),
            )

            # OPTIMIZATION: Prepare lightweight data for OpenAI to reduce memory usage
            # Only include essential fields instead of full objects
            lightweight_flights = []
            for flight in api_results["flights"][:6]:  # Reduced to 6 flights max
                lightweight_flights.append(
                    {
                        "id": flight.get("id"),
                        "price": flight.get("price"),
                        "searched_destination": flight.get("searched_destination"),
                        "total_amount": flight.get("total_amount"),
                        "owner": flight.get("owner", {}),
                    }
                )

            lightweight_hotels = []
            for hotel in api_results["hotels"][:9]:  # Reduced to 9 hotels max
                lightweight_hotels.append(
                    {
                        "id": hotel.get("id"),
                        "name": hotel.get("name"),
                        "price_per_night": hotel.get("price_per_night"),
                        "rating": hotel.get("rating"),
                        "searched_destination": hotel.get("searched_destination"),
                    }
                )

            lightweight_activities = []
            for activity in api_results["activities"][
                :12
            ]:  # Reduced to 12 activities max
                lightweight_activities.append(
                    {
                        "id": activity.get("id"),
                        "name": activity.get("name"),
                        "price": activity.get("price"),
                        "category": activity.get("category"),
                        "searched_destination": activity.get("searched_destination"),
                    }
                )

            # Store reference to api_results before clearing (needed for manual generation fallback)
            api_results_backup = {
                "flights": api_results["flights"],
                "hotels": api_results["hotels"],
                "activities": api_results["activities"],
            }

            # OPTIMIZATION: Clear original large data structures before OpenAI call
            del api_results
            gc.collect()  # Force garbage collection to free memory

            # Generate 3 itinerary options with selected dates
            openai_available = False
            try:
                # Try OpenAI first if available
                if "openai_service" in locals():
                    options_data = openai_service.generate_three_itinerary_options(
                        member_preferences=member_prefs,
                        flight_results=lightweight_flights,
                        hotel_results=lightweight_hotels,
                        activity_results=lightweight_activities,
                        selected_dates={
                            "start_date": search_start_date.strftime("%Y-%m-%d"),
                            "end_date": search_end_date.strftime("%Y-%m-%d"),
                            "duration_days": (search_end_date - search_start_date).days,
                        },
                    )
                    openai_available = True
                else:
                    raise ValueError("OpenAI service not available")
            except Exception as e:
                # OpenAI not available - generate options manually
                print(f"[WARNING] OpenAI not available for option generation: {str(e)}")
                print("[INFO] Generating options manually from available data...")

                # Use backup data if lightweight data is insufficient
                manual_flights = (
                    lightweight_flights
                    if lightweight_flights
                    else [
                        {
                            "id": f.get("id"),
                            "price": f.get("price"),
                            "searched_destination": f.get("searched_destination"),
                        }
                        for f in api_results_backup.get("flights", [])[:20]
                    ]
                )
                manual_hotels = (
                    lightweight_hotels
                    if lightweight_hotels
                    else [
                        {
                            "id": h.get("id"),
                            "name": h.get("name"),
                            "price_per_night": h.get("price_per_night"),
                            "rating": h.get("rating"),
                            "searched_destination": h.get("searched_destination"),
                        }
                        for h in api_results_backup.get("hotels", [])[:20]
                    ]
                )
                manual_activities = (
                    lightweight_activities
                    if lightweight_activities
                    else [
                        {
                            "id": a.get("id"),
                            "name": a.get("name"),
                            "price": a.get("price"),
                            "category": a.get("category"),
                            "searched_destination": a.get("searched_destination"),
                        }
                        for a in api_results_backup.get("activities", [])[:20]
                    ]
                )

                # Generate options manually based on budget tiers
                options_data = _generate_options_manually(
                    member_prefs=member_prefs,
                    flight_results=manual_flights,
                    hotel_results=manual_hotels,
                    activity_results=manual_activities,
                    search=search,
                    group=group,
                )
            finally:
                # Clean up lightweight data after API call
                del lightweight_flights, lightweight_hotels, lightweight_activities
                gc.collect()

            def _normalize_text(value, default=""):
                if value is None:
                    return default
                if isinstance(value, (int, float)):
                    return str(value)
                return str(value)

            def _ensure_list(value):
                if not value:
                    return []
                if isinstance(value, list):
                    return value
                if isinstance(value, tuple):
                    return list(value)
                return [value]

            def _safe_decimal(value, default=0.0):
                from decimal import Decimal, InvalidOperation

                if value in (None, ""):
                    return Decimal(default)
                try:
                    return Decimal(str(value))
                except (InvalidOperation, TypeError, ValueError):
                    return Decimal(default)

            raw_options = options_data.get("options") or []
            if isinstance(raw_options, dict):
                raw_options = [raw_options]
            elif not isinstance(raw_options, (list, tuple)):
                raw_options = list(raw_options) if raw_options else []

            # Create all options in database (5-8 options)
            all_options_created = []
            for idx, option_data in enumerate(raw_options):
                if not isinstance(option_data, dict):
                    try:
                        option_data = dict(option_data)
                    except Exception:
                        continue

                option_letter = option_data.get("option_letter")
                if not option_letter:
                    option_letter = chr(ord("A") + idx)

                title = _normalize_text(
                    option_data.get("title"), f"Option {option_letter}"
                )
                description = _normalize_text(option_data.get("description"), "")
                ai_reasoning = _normalize_text(option_data.get("ai_reasoning"), "")
                compromise_copy = _normalize_text(
                    option_data.get("compromise_explanation", ""), ""
                )

                selected_flight_id = option_data.get("selected_flight_id")
                if selected_flight_id is not None:
                    selected_flight_id = _normalize_text(selected_flight_id)

                selected_hotel_id = option_data.get("selected_hotel_id")
                if selected_hotel_id is not None:
                    selected_hotel_id = _normalize_text(selected_hotel_id)

                raw_activity_ids = _ensure_list(
                    option_data.get("selected_activity_ids")
                )
                activity_ids = [
                    _normalize_text(activity_id)
                    for activity_id in raw_activity_ids
                    if _normalize_text(activity_id)
                ]

                # Get intended destination from option_data (this is the correct destination)
                intended_dest = _normalize_text(
                    option_data.get("intended_destination"), ""
                )
                if not intended_dest:
                    # Fallback 1: extract from title
                    if " to " in title:
                        intended_dest = title.split(" to ")[-1].strip()
                    elif " in " in title:
                        intended_dest = title.split(" in ")[-1].strip()
                    elif " at " in title:
                        intended_dest = title.split(" at ")[-1].strip()

                # Fallback 2: Try to get destination from flight_id or hotel_id
                if not intended_dest:
                    flight_id = option_data.get("selected_flight_id")
                    hotel_id = option_data.get("selected_hotel_id")

                    if flight_id:
                        # Look up the flight to get its destination
                        flight = FlightResult.objects.filter(
                            search=search, external_id=flight_id
                        ).first()
                        if flight and flight.searched_destination:
                            intended_dest = flight.searched_destination
                            print(
                                f"  [FALLBACK] Extracted destination from flight: {intended_dest}"
                            )

                    if not intended_dest and hotel_id:
                        # Look up the hotel to get its destination
                        hotel = HotelResult.objects.filter(
                            search=search, external_id=hotel_id
                        ).first()
                        if hotel and hotel.searched_destination:
                            intended_dest = hotel.searched_destination
                            print(
                                f"  [FALLBACK] Extracted destination from hotel: {intended_dest}"
                            )

                # Fallback 3: Use first available destination from search results
                if not intended_dest:
                    # Get any destination from available flights or hotels
                    first_flight = FlightResult.objects.filter(search=search).first()
                    if first_flight and first_flight.searched_destination:
                        intended_dest = first_flight.searched_destination
                        print(
                            f"  [FALLBACK] Using first available flight destination: {intended_dest}"
                        )
                    else:
                        first_hotel = HotelResult.objects.filter(search=search).first()
                        if first_hotel and first_hotel.searched_destination:
                            intended_dest = first_hotel.searched_destination
                            print(
                                f"  [FALLBACK] Using first available hotel destination: {intended_dest}"
                            )

                print(
                    f"[DB LOOKUP] Option {option_letter}: Looking for flight/hotel for destination: {intended_dest}"
                )

                # Get selected flight - MUST match intended destination
                selected_flight = None
                flight_id = selected_flight_id
                if flight_id:
                    # First try to find flight by ID (exact match)
                    flight_by_id = FlightResult.objects.filter(
                        search=search, external_id=flight_id
                    ).first()

                    if flight_by_id:
                        # Check if destination matches (exact or contains)
                        flight_dest = flight_by_id.searched_destination or ""
                        if intended_dest and (
                            intended_dest.lower() in flight_dest.lower()
                            or flight_dest.lower() in intended_dest.lower()
                        ):
                            selected_flight = flight_by_id
                            print(
                                f"  [OK] Flight found by ID: {selected_flight.airline} to {selected_flight.searched_destination}"
                            )
                        else:
                            print(
                                f"  [WARNING] Flight ID '{flight_id}' exists but destination mismatch: '{flight_dest}' vs '{intended_dest}'"
                            )
                            # Try to find a flight that matches the intended destination
                            if intended_dest:
                                # Try exact match first
                                selected_flight = FlightResult.objects.filter(
                                    search=search, searched_destination=intended_dest
                                ).first()

                                # If no exact match, try flexible matching
                                if not selected_flight:
                                    all_flights = FlightResult.objects.filter(
                                        search=search
                                    )
                                    for flight in all_flights:
                                        flight_dest = (
                                            flight.searched_destination or ""
                                        ).lower()
                                        intended_lower = intended_dest.lower()
                                        if (
                                            intended_lower in flight_dest
                                            or flight_dest in intended_lower
                                        ):
                                            selected_flight = flight
                                            print(
                                                f"  [FIX] Found matching flight (flexible): {selected_flight.airline} to {selected_flight.searched_destination}"
                                            )
                                            break

                                if selected_flight:
                                    print(
                                        f"  [FIX] Found matching flight: {selected_flight.airline} to {selected_flight.searched_destination}"
                                    )
                                else:
                                    # Last resort: use the flight by ID anyway
                                    selected_flight = flight_by_id
                                    print(
                                        f"  [FALLBACK] Using flight by ID despite destination mismatch: {selected_flight.airline} to {selected_flight.searched_destination}"
                                    )

                # If still no flight, find any flight for this destination (flexible matching)
                if not selected_flight and intended_dest:
                    print(f"  [RETRY] Looking for any flight to {intended_dest}...")
                    # Try exact match first
                    selected_flight = FlightResult.objects.filter(
                        search=search, searched_destination=intended_dest
                    ).first()

                    # If no exact match, try flexible matching
                    if not selected_flight:
                        all_flights = FlightResult.objects.filter(search=search)
                        for flight in all_flights:
                            flight_dest = (flight.searched_destination or "").lower()
                            intended_lower = intended_dest.lower()
                            if (
                                intended_lower in flight_dest
                                or flight_dest in intended_lower
                            ):
                                selected_flight = flight
                                print(
                                    f"  [OK] Found flight (flexible match): {selected_flight.airline} to {selected_flight.searched_destination}"
                                )
                                break

                    if not selected_flight:
                        # Last resort: get any flight from this search
                        selected_flight = FlightResult.objects.filter(
                            search=search
                        ).first()
                        if selected_flight:
                            print(
                                f"  [FALLBACK] Using any available flight: {selected_flight.airline} to {selected_flight.searched_destination}"
                            )

                # Get selected hotel - MUST match intended destination
                selected_hotel = None
                hotel_id = selected_hotel_id

                if hotel_id:
                    # First try to find hotel by ID (exact match)
                    hotel_by_id = HotelResult.objects.filter(
                        search=search, external_id=hotel_id
                    ).first()

                    if hotel_by_id:
                        # Check if destination matches (exact or contains)
                        hotel_dest = hotel_by_id.searched_destination or ""
                        if intended_dest and (
                            intended_dest.lower() in hotel_dest.lower()
                            or hotel_dest.lower() in intended_dest.lower()
                        ):
                            selected_hotel = hotel_by_id
                            print(
                                f"  [OK] Hotel found by ID: {selected_hotel.name} in {selected_hotel.searched_destination}"
                            )
                        else:
                            print(
                                f"  [WARNING] Hotel ID '{hotel_id}' exists but destination mismatch: '{hotel_dest}' vs '{intended_dest}'"
                            )
                            # Try to find a hotel that matches the intended destination
                            if intended_dest:
                                # Try exact match first
                                selected_hotel = HotelResult.objects.filter(
                                    search=search, searched_destination=intended_dest
                                ).first()

                                # If no exact match, try flexible matching
                                if not selected_hotel:
                                    all_hotels = HotelResult.objects.filter(
                                        search=search
                                    )
                                    for hotel in all_hotels:
                                        hotel_dest = (
                                            hotel.searched_destination or ""
                                        ).lower()
                                        intended_lower = intended_dest.lower()
                                        if (
                                            intended_lower in hotel_dest
                                            or hotel_dest in intended_lower
                                        ):
                                            selected_hotel = hotel
                                            print(
                                                f"  [FIX] Found matching hotel (flexible): {selected_hotel.name} in {selected_hotel.searched_destination}"
                                            )
                                            break

                                if selected_hotel:
                                    print(
                                        f"  [FIX] Found matching hotel: {selected_hotel.name} in {selected_hotel.searched_destination}"
                                    )
                                else:
                                    # Last resort: use the hotel by ID anyway
                                    selected_hotel = hotel_by_id
                                    print(
                                        f"  [FALLBACK] Using hotel by ID despite destination mismatch: {selected_hotel.name} in {selected_hotel.searched_destination}"
                                    )

                # If still no hotel, find any hotel for this destination (flexible matching)
                if not selected_hotel and intended_dest:
                    print(f"  [RETRY] Looking for any hotel in {intended_dest}...")
                    # Try exact match first
                    selected_hotel = HotelResult.objects.filter(
                        search=search, searched_destination=intended_dest
                    ).first()

                    # If no exact match, try flexible matching
                    if not selected_hotel:
                        all_hotels = HotelResult.objects.filter(search=search)
                        for hotel in all_hotels:
                            hotel_dest = (hotel.searched_destination or "").lower()
                            intended_lower = intended_dest.lower()
                            if (
                                intended_lower in hotel_dest
                                or hotel_dest in intended_lower
                            ):
                                selected_hotel = hotel
                                print(
                                    f"  [OK] Found hotel (flexible match): {selected_hotel.name} in {selected_hotel.searched_destination}"
                                )
                                break

                    if not selected_hotel:
                        # Last resort: get any hotel from this search
                        selected_hotel = HotelResult.objects.filter(
                            search=search
                        ).first()
                        if selected_hotel:
                            print(
                                f"  [FALLBACK] Using any available hotel: {selected_hotel.name} in {selected_hotel.searched_destination}"
                            )

                # Use intended destination as the option destination
                option_destination = intended_dest

                # LAST RESORT: If still no hotel, this is an error
                if not selected_hotel:
                    print(
                        f"  [ERROR] No hotels found for destination {intended_dest} for Option {option_data.get('option_letter', '?')}"
                    )

                # Calculate total cost explicitly: flight + hotel
                total_cost = 0.0
                if selected_flight:
                    total_cost += float(selected_flight.price)
                if selected_hotel:
                    total_cost += float(selected_hotel.total_price)

                # If OpenAI provided a cost estimate, use the higher of the two to ensure accuracy
                ai_estimated_cost = float(
                    _safe_decimal(option_data.get("estimated_total_cost", 0))
                )
                # Use explicit calculation (flight + hotel) as the source of truth
                final_total_cost = total_cost if total_cost > 0 else ai_estimated_cost

                # Calculate cost per person
                cost_per_person = (
                    final_total_cost / group.member_count
                    if group.member_count > 0
                    else final_total_cost
                )

                # Create option
                option = GroupItineraryOption.objects.create(
                    group=group,
                    consensus=consensus,
                    option_letter=option_letter,
                    title=title,
                    description=description,
                    destination=option_destination,  # Store the specific destination
                    search=search,
                    selected_flight=selected_flight,
                    selected_hotel=selected_hotel,
                    selected_activities=json.dumps(activity_ids),
                    estimated_total_cost=final_total_cost,
                    cost_per_person=cost_per_person,
                    ai_reasoning=ai_reasoning,
                    compromise_explanation=compromise_copy,
                    status="pending",  # All start as pending
                    display_order=0,  # Will be set when activated
                )
                all_options_created.append(option)

            # Randomly select one option to be active, rest stay pending
            if all_options_created:
                active_option = random.choice(all_options_created)
                active_option.status = "active"
                active_option.display_order = 1
                active_option.save()
                print(f"[OK] {len(all_options_created)} itinerary options generated!")
                print(
                    f"[OK] Option {active_option.option_letter} randomly selected as first active option"
                )
                print(f"[OK] {len(all_options_created) - 1} options stored as pending")
            else:
                print("[WARNING] No options were created!")
            # Return JSON response for AJAX call instead of redirect
            return JsonResponse(
                {
                    "success": True,
                    "message": f"{len(all_options_created)} itinerary options generated! One option is now active for voting.",
                }
            )

        except Exception as e:
            import traceback
            from django.conf import settings

            error_details = traceback.format_exc()
            print(f"[ERROR] Error generating options: {str(e)}")
            # Only print full traceback in DEBUG mode to avoid exposing internal details
            if settings.DEBUG:
                print(f"Full traceback:\n{error_details}")
            else:
                print(
                    f"[ERROR] See server logs for full traceback (DEBUG mode disabled)"
                )
            # Return JSON error response for AJAX call with safe error message
            return JsonResponse(
                {
                    "success": False,
                    "error": "Error generating voting options. Please try again or contact support.",
                },
                status=500,
            )

    # GET request - show generation form
    members_count = GroupMember.objects.filter(group=group).count()
    prefs_count = TripPreference.objects.filter(group=group, is_completed=True).count()

    context = {
        "group": group,
        "members_count": members_count,
        "prefs_count": prefs_count,
    }
    return render(request, "ai_implementation/generate_voting_options.html", context)


@login_required
def view_voting_options(request, group_id):
    """Display the 3 itinerary options for group members to vote on"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect("travel_groups:group_list")

    # Get latest consensus with options
    consensus = (
        GroupConsensus.objects.filter(group=group, is_active=True)
        .order_by("-created_at")
        .first()
    )

    if not consensus:
        messages.warning(
            request, "No voting options available yet. Generate options first."
        )
        return redirect("ai_implementation:generate_voting_options", group_id=group.id)

    # Get the 3 options
    options = GroupItineraryOption.objects.filter(
        group=group, consensus=consensus
    ).select_related("selected_flight", "selected_hotel")

    if not options.exists():
        messages.warning(request, "No options found. Please generate them first.")
        return redirect("ai_implementation:generate_voting_options", group_id=group.id)

    # Check if user has voted
    user_vote = ItineraryVote.objects.filter(group=group, user=request.user).first()

    # Get activities for each option (filtered by destination)
    options_with_activities = []
    for option in options:
        activity_ids = (
            json.loads(option.selected_activities) if option.selected_activities else []
        )

        # Get all activities, then filter by destination
        if activity_ids:
            all_activities = ActivityResult.objects.filter(
                search=option.search, external_id__in=activity_ids
            )

            # Filter to match option's destination
            activities = []
            for activity in all_activities:
                activity_destination = activity.searched_destination or ""

                # If option has destination, filter by it
                if option.destination:
                    if activity_destination == option.destination:
                        activities.append(activity)
                else:
                    # No destination filtering - include all
                    activities.append(activity)

            # If no activities after filtering, fall back to showing all
            if not activities and all_activities:
                activities = list(all_activities)
        else:
            activities = []

        options_with_activities.append({"option": option, "activities": activities})

    # Get voting stats
    total_members = GroupMember.objects.filter(group=group).count()
    votes_cast = ItineraryVote.objects.filter(group=group).count()

    context = {
        "group": group,
        "consensus": consensus,
        "options_with_activities": options_with_activities,
        "user_vote": user_vote,
        "total_members": total_members,
        "votes_cast": votes_cast,
        "voting_complete": votes_cast >= total_members,
    }
    return render(request, "ai_implementation/view_voting_options.html", context)


@login_required
@require_http_methods(["POST"])
def cast_vote(request, group_id, option_id):
    """Cast a vote for an itinerary option"""
    group = get_object_or_404(TravelGroup, id=group_id)
    option = get_object_or_404(GroupItineraryOption, id=option_id, group=group)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not a group member"})

    total_members = GroupMember.objects.filter(group=group).count()
    option_votes_qs = ItineraryVote.objects.filter(group=group, option=option)
    votes_cast_existing = option_votes_qs.count()
    yes_votes_existing = option_votes_qs.exclude(comment="ROLL_AGAIN").count()

    if option.status in ("accepted", "completed") or option.is_winner:
        return JsonResponse(
            {
                "success": False,
                "error": "This option has already been accepted by the group.",
            }
        )

    if (
        option.status == "active"
        and votes_cast_existing >= total_members
        and yes_votes_existing == total_members
    ):
        option.status = "accepted"
        option.is_winner = True
        option.save(update_fields=["status", "is_winner"])
        return JsonResponse(
            {
                "success": False,
                "error": "This option already has unanimous approval.",
            }
        )

    # Check if user already voted on THIS OPTION
    existing_vote = ItineraryVote.objects.filter(
        group=group, user=request.user, option=option
    ).first()

    if existing_vote:
        # Update existing vote (user changed their mind)
        existing_vote.comment = request.POST.get("comment", "")
        existing_vote.save()
        message = "Vote updated successfully!"
    else:
        # Check if user has a vote for a different option
        other_vote = ItineraryVote.objects.filter(
            group=group, user=request.user
        ).first()
        if other_vote:
            # Update existing vote to point to current option
            old_option = other_vote.option
            other_vote.option = option
            other_vote.comment = request.POST.get("comment", "")
            other_vote.save()
            # Update old option's vote count
            old_option.update_vote_count()
            message = "Vote updated successfully!"
        else:
            # New vote
            ItineraryVote.objects.create(
                option=option,
                user=request.user,
                group=group,
                comment=request.POST.get("comment", ""),
            )
            message = "Vote cast successfully!"

    # Ensure option's vote count is updated
    option.update_vote_count()

    # Check if all members have voted on THIS OPTION
    votes_cast = ItineraryVote.objects.filter(group=group, option=option).count()

    print(f"[DEBUG cast_vote] Option {option.id} ({option.title[:50]}...)")
    print(
        f"[DEBUG cast_vote] Votes cast on this option: {votes_cast}, Total members: {total_members}"
    )
    print(
        f"[DEBUG cast_vote] Option status: {option.status}, is_winner: {option.is_winner}"
    )

    # Get the active option - use the option we're voting on if it's active
    active_option = (
        option
        if option.status == "active"
        else GroupItineraryOption.objects.filter(group=group, status="active").first()
    )

    unanimous = False
    advanced = False
    all_voted = votes_cast >= total_members

    print(
        f"[DEBUG cast_vote] Active option: {active_option.id if active_option else None}"
    )
    print(
        f"[DEBUG cast_vote] All voted: {all_voted}, Option is active: {option.status == 'active'}"
    )

    # Only check for advancement if we're voting on the active option
    if active_option and option.id == active_option.id and all_voted:
        # Check if all votes are "yes" votes (not ROLL_AGAIN) for the active option
        yes_votes_for_active = (
            ItineraryVote.objects.filter(group=group, option=active_option)
            .exclude(comment="ROLL_AGAIN")
            .count()
        )

        print(
            f"[DEBUG cast_vote] Yes votes (excluding ROLL_AGAIN): {yes_votes_for_active}, Total members: {total_members}"
        )

        if yes_votes_for_active == total_members:
            # Unanimous yes vote! Mark as accepted
            print(
                f"[DEBUG cast_vote] UNANIMOUS VOTE DETECTED! Marking option as accepted..."
            )
            active_option.status = "accepted"
            active_option.is_winner = True
            active_option.save(update_fields=["status", "is_winner"])

            # Refresh from database to confirm save
            active_option.refresh_from_db()
            print(
                f"[SUCCESS] Option {active_option.id} marked as accepted and winner for group {group.id}"
            )
            print(
                f"[DEBUG] Status: {active_option.status}, is_winner: {active_option.is_winner}"
            )
            print(f"[DEBUG] Group ID: {group.id}, Group Name: {group.name}")
            print(
                f"[DEBUG] Total members: {total_members}, Yes votes: {yes_votes_for_active}"
            )
            unanimous = True
            message = (
                "🎉 Unanimous vote! This option has been selected as the group trip!"
            )
        else:
            print(
                f"[DEBUG cast_vote] Not unanimous - {yes_votes_for_active} yes votes out of {total_members} members"
            )
            # Not unanimous - someone voted "no" (ROLL_AGAIN)
            # Reject and load next pending option automatically
            active_option.status = "rejected"
            active_option.save()

            # Clear all votes for the rejected option (so members can vote on next option)
            ItineraryVote.objects.filter(group=group, option=active_option).delete()

            # Get next pending option (already generated and stored)
            pending_options = list(
                GroupItineraryOption.objects.filter(
                    group=group, status="pending"
                ).order_by("display_order", "option_letter")
            )

            if pending_options:
                # Activate the first pending option
                next_option = pending_options[0]
                next_option.status = "active"

                # Set display order (increment from highest existing)
                max_order = (
                    GroupItineraryOption.objects.filter(group=group).aggregate(
                        max_order=models.Max("display_order")
                    )["max_order"]
                    or 0
                )
                next_option.display_order = max_order + 1
                next_option.save()

                advanced = True
                message = f"Not unanimous. Option {active_option.option_letter} rejected. Advanced to Option {next_option.option_letter}."
            else:
                # No more pending options - try to generate a new one
                search = active_option.search
                consensus = active_option.consensus

                # Get member preferences for generating new option
                trip_preferences = TripPreference.objects.filter(
                    group=group, is_completed=True
                )
                member_prefs = []
                for pref in trip_preferences:
                    member_prefs.append(
                        {
                            "user": pref.user.username,
                            "destination": pref.destination,
                            "start_date": pref.start_date.strftime("%Y-%m-%d"),
                            "end_date": pref.end_date.strftime("%Y-%m-%d"),
                            "budget": str(pref.budget),
                            "travel_method": pref.travel_method,
                            "rental_car": pref.rental_car,
                            "accommodation_preference": pref.accommodation_preference
                            or "",
                            "activity_preferences": pref.activity_preferences or "",
                            "dietary_restrictions": pref.dietary_restrictions or "",
                            "accessibility_needs": pref.accessibility_needs or "",
                            "notes": pref.additional_notes or "",
                        }
                    )

                # Generate a new option
                next_option = _generate_single_new_option(
                    group, consensus, search, member_prefs
                )

                if next_option:
                    advanced = True
                    message = f"Not unanimous. Option {active_option.option_letter} rejected. Generated new Option {next_option.option_letter}."
                else:
                    message = f"Not unanimous. Option {active_option.option_letter} rejected. No more options available. Please generate new trip options."

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "votes_cast": votes_cast,
            "total_members": total_members,
            "unanimous": unanimous,
            "all_voted": all_voted,
            "active_option_id": str(active_option.id) if active_option else None,
            "advanced": advanced,
        }
    )


@login_required
def voting_results(request, group_id):
    """Display voting results and winner"""
    group = get_object_or_404(TravelGroup, id=group_id)

    # Verify user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, "You are not a member of this group.")
        return redirect("travel_groups:group_list")

    # Get latest consensus
    consensus = (
        GroupConsensus.objects.filter(group=group, is_active=True)
        .order_by("-created_at")
        .first()
    )

    if not consensus:
        messages.warning(request, "No voting session found.")
        return redirect("travel_groups:group_detail", group_id=group.id)

    # Get options with votes
    options = GroupItineraryOption.objects.filter(
        group=group, consensus=consensus
    ).order_by("-vote_count")

    # Get winner
    winner = options.filter(is_winner=True).first()

    # Get all votes with user info
    votes = ItineraryVote.objects.filter(group=group).select_related("user", "option")

    # Get voting stats
    total_members = GroupMember.objects.filter(group=group).count()
    votes_cast = ItineraryVote.objects.filter(group=group).count()

    # Get activities for winner (filtered by destination)
    winner_activities = []
    if winner and winner.selected_activities:
        activity_ids = json.loads(winner.selected_activities)
        all_winner_activities = ActivityResult.objects.filter(
            search=winner.search, external_id__in=activity_ids
        )

        # Filter activities to match winner's destination
        for activity in all_winner_activities:
            activity_destination = activity.searched_destination or ""

            # If winner has destination, filter by it
            if winner.destination:
                if activity_destination == winner.destination:
                    winner_activities.append(activity)
            else:
                # No destination filtering - include all
                winner_activities.append(activity)

        # If no activities after filtering, fall back to showing all
        if not winner_activities and all_winner_activities:
            winner_activities = list(all_winner_activities)

    context = {
        "group": group,
        "consensus": consensus,
        "options": options,
        "winner": winner,
        "votes": votes,
        "total_members": total_members,
        "votes_cast": votes_cast,
        "winner_activities": winner_activities,
    }
    return render(request, "ai_implementation/voting_results.html", context)
