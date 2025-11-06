"""
Views for AI Implementation
Handles travel search requests, API calls, and consolidated result display.
"""

import json
import gc  # For garbage collection to free memory
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction

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
from .duffel_connector import DuffelAggregator

from travel_groups.models import TravelGroup, GroupMember, TripPreference


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

    # If results don't exist or user requested refresh
    if not results_exist or request.GET.get("refresh") == "true":
        # Perform the search
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
        # Initialize Duffel API aggregator (falls back to mock data if no API key)
        aggregator = DuffelAggregator()

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

        # Search all APIs
        api_results = aggregator.search_all(
            destination=search.destination,
            origin=search.origin,
            start_date=search.start_date.strftime("%Y-%m-%d"),
            end_date=search.end_date.strftime("%Y-%m-%d"),
            adults=search.adults,
            rooms=search.rooms,
            preferences=preferences,
        )

        # Save raw results to database
        with transaction.atomic():
            # Delete old results if any
            FlightResult.objects.filter(search=search).delete()
            HotelResult.objects.filter(search=search).delete()
            ActivityResult.objects.filter(search=search).delete()

            # Save flight results
            for flight_data in api_results["flights"]:
                FlightResult.objects.create(
                    search=search,
                    external_id=flight_data.get("id", "N/A"),
                    airline=flight_data.get("airline", "Unknown"),
                    price=flight_data.get("price", 0),
                    currency=flight_data.get("currency", "USD"),
                    departure_time=flight_data.get("departure_time", search.start_date),
                    arrival_time=flight_data.get("arrival_time", search.start_date),
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

        # Get dates from JSON body or use None as fallback
        selected_start_date = body_data.get("start_date")
        selected_end_date = body_data.get("end_date")

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
            f"🌍 Found {len(destinations_list)} unique destinations from members: {destinations_list}"
        )

        # Use first preference as base for dates
        first_pref = trip_preferences.first()

        # Use selected dates if provided, otherwise use first preference dates
        if selected_start_date and selected_end_date:
            search_start_date = datetime.strptime(
                selected_start_date, "%Y-%m-%d"
            ).date()
            search_end_date = datetime.strptime(selected_end_date, "%Y-%m-%d").date()
            print(f"📅 Using selected dates: {search_start_date} to {search_end_date}")
        else:
            search_start_date = first_pref.start_date
            search_end_date = first_pref.end_date
            print(
                f"📅 Using preference dates: {search_start_date} to {search_end_date}"
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
            aggregator = DuffelAggregator()

            # Combine results from all destinations
            all_flights = []
            all_hotels = []
            all_activities = []

            for destination in destinations_list:
                print(f"\n🔍 Searching for {destination}...")

                api_results = aggregator.search_all(
                    destination=destination,
                    origin=None,
                    start_date=search_start_date.strftime("%Y-%m-%d"),
                    end_date=search_end_date.strftime("%Y-%m-%d"),
                    adults=group.member_count,
                    rooms=search.rooms,
                )

                # Tag each result with its destination for tracking
                for flight in api_results["flights"]:
                    flight["searched_destination"] = destination
                    all_flights.append(flight)

                for hotel in api_results["hotels"]:
                    hotel["searched_destination"] = destination
                    all_hotels.append(hotel)

                for activity in api_results["activities"]:
                    activity["searched_destination"] = destination
                    all_activities.append(activity)

            print(f"\n✅ Combined Results:")
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
                print(f"\n📊 Hotels by Destination:")
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
                    FlightResult.objects.create(
                        search=search,
                        external_id=flight_data.get("id", "N/A"),
                        airline=flight_data.get("airline", "Unknown"),
                        price=flight_data.get("price", 0),
                        currency=flight_data.get("currency", "USD"),
                        departure_time=flight_data.get(
                            "departure_time", search.start_date
                        ),
                        arrival_time=flight_data.get("arrival_time", search.start_date),
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

            # Generate consensus first
            openai_service = OpenAIService()
            consensus_data = openai_service.generate_group_consensus(member_prefs)

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

            # OPTIMIZATION: Clear original large data structures before OpenAI call
            del api_results
            gc.collect()  # Force garbage collection to free memory

            # Generate 3 itinerary options with selected dates
            try:
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
            except Exception as e:
                # Handle OpenAI timeout or memory errors gracefully
                print(f"❌ Error generating itinerary options: {str(e)}")
                messages.error(
                    request,
                    f"Error generating itinerary options. Please try again with fewer destinations or a smaller group.",
                )
                return redirect("travel_groups:group_detail", group_id=group.id)
            finally:
                # Clean up lightweight data after API call
                del lightweight_flights, lightweight_hotels, lightweight_activities
                gc.collect()

            # Create the 3 options in database
            for option_data in options_data.get("options", []):
                # Get selected flight
                selected_flight = None
                if option_data.get("selected_flight_id"):
                    selected_flight = FlightResult.objects.filter(
                        search=search, external_id=option_data["selected_flight_id"]
                    ).first()

                # Get selected hotel
                selected_hotel = None
                option_destination = None
                hotel_id = option_data.get("selected_hotel_id")

                if hotel_id:
                    selected_hotel = HotelResult.objects.filter(
                        search=search, external_id=hotel_id
                    ).first()

                    if selected_hotel:
                        # Extract destination from hotel's searched_destination field
                        option_destination = selected_hotel.searched_destination or ""
                        print(
                            f"  ✅ Hotel found: {selected_hotel.name} in {option_destination}"
                        )
                    else:
                        print(
                            f"  ⚠️ Hotel ID '{hotel_id}' not found in database for Option {option_data['option_letter']}"
                        )

                # Try to get destination from flight if hotel doesn't have it
                if not option_destination and selected_flight:
                    option_destination = selected_flight.searched_destination or ""

                # FALLBACK: If no hotel was found but we have a destination, pick the first available hotel for that destination
                if not selected_hotel and option_destination:
                    print(f"  🔄 Looking for fallback hotel in {option_destination}...")
                    fallback_hotel = HotelResult.objects.filter(
                        search=search, searched_destination=option_destination
                    ).first()
                    if fallback_hotel:
                        selected_hotel = fallback_hotel
                        print(f"  ✅ Fallback hotel selected: {fallback_hotel.name}")

                # LAST RESORT: If still no hotel, pick the first available hotel from any destination
                if not selected_hotel:
                    selected_hotel = HotelResult.objects.filter(search=search).first()
                    if selected_hotel:
                        print(f"  ⚠️ Using any available hotel: {selected_hotel.name}")
                    else:
                        print(
                            f"  ❌ No hotels found at all for Option {option_data['option_letter']}"
                        )

                # Create option
                GroupItineraryOption.objects.create(
                    group=group,
                    consensus=consensus,
                    option_letter=option_data["option_letter"],
                    title=option_data["title"],
                    description=option_data["description"],
                    destination=option_destination,  # Store the specific destination
                    search=search,
                    selected_flight=selected_flight,
                    selected_hotel=selected_hotel,
                    selected_activities=json.dumps(
                        option_data.get("selected_activity_ids", [])
                    ),
                    estimated_total_cost=option_data["estimated_total_cost"],
                    cost_per_person=option_data["cost_per_person"],
                    ai_reasoning=option_data["ai_reasoning"],
                    compromise_explanation=option_data.get(
                        "compromise_explanation", ""
                    ),
                )

            print("✅ 3 itinerary options generated!")
            # Return JSON response for AJAX call instead of redirect
            return JsonResponse(
                {
                    "success": True,
                    "message": "3 itinerary options generated! Group members can now vote.",
                }
            )

        except Exception as e:
            print(f"❌ Error generating options: {str(e)}")
            # Return JSON error response for AJAX call
            return JsonResponse({"success": False, "error": str(e)}, status=500)

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

    # Check if user already voted
    existing_vote = ItineraryVote.objects.filter(group=group, user=request.user).first()

    if existing_vote:
        # Change vote
        existing_vote.option = option
        existing_vote.comment = request.POST.get("comment", "")
        existing_vote.save()
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

    # Check if all members have voted
    total_members = GroupMember.objects.filter(group=group).count()
    votes_cast = ItineraryVote.objects.filter(group=group).count()

    if votes_cast >= total_members:
        # Determine winner
        winner = (
            GroupItineraryOption.objects.filter(group=group)
            .order_by("-vote_count")
            .first()
        )

        if winner:
            # Mark as winner
            GroupItineraryOption.objects.filter(group=group).update(is_winner=False)
            winner.is_winner = True
            winner.save()

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "votes_cast": votes_cast,
            "total_members": total_members,
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
