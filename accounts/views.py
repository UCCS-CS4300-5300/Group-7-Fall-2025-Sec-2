from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from .models import UserProfile, Itinerary
from .forms import SignUpForm, ItineraryForm
import json

def home_view(request):
    """Homepage view"""
    print("DEBUG: Rendering accounts/home.html template")
    return render(request, 'accounts/home.html')

def login_view(request):
    """Login page view"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to find user by email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'accounts/login.html')

def signup_view(request):
    """Sign up page view"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                # Create user profile
                UserProfile.objects.create(
                    user=user,
                    phone_number=form.cleaned_data['phone_number']
                )
                username = form.cleaned_data.get('username')
                messages.success(request, f'Account created for {username}!')
                login(request, user)
                return redirect('accounts:dashboard')
            except Exception as e:
                messages.error(request, f'Error creating account: {e}')
    else:
        form = SignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def dashboard_view(request):
    """User dashboard view"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Create a UserProfile if it doesn't exist (for users created outside of signup)
        user_profile = UserProfile.objects.create(
            user=request.user,
            phone_number=''  # Empty phone number for users created outside signup
        )
    
    saved_itineraries = Itinerary.objects.filter(user=request.user, is_active=False)
    active_trips = Itinerary.objects.filter(user=request.user, is_active=True)
    
    # Get user's groups for trip planning
    from travel_groups.models import GroupMember
    user_groups = GroupMember.objects.filter(user=request.user).select_related('group')
    
    # Get accepted group trips (trips that were unanimously selected)
    from ai_implementation.models import GroupItineraryOption
    from travel_groups.models import TravelGroup
    
    # Get all groups the user is a member of
    user_group_ids = list(user_groups.values_list('group_id', flat=True))
    
    # Debug logging
    print(f"[DEBUG] User {request.user.username} is member of groups: {user_group_ids}")
    
    # Get accepted itinerary options for those groups
    if user_group_ids:
        accepted_group_trips = GroupItineraryOption.objects.filter(
            group_id__in=user_group_ids,
            status='accepted',
            is_winner=True
        ).select_related(
            'group', 
            'selected_flight', 
            'selected_hotel',
            'search'
        ).order_by('-created_at')
        
        print(f"[DEBUG] Found {accepted_group_trips.count()} accepted trips for user {request.user.username}")
        for trip in accepted_group_trips:
            print(f"[DEBUG]   - {trip.title} (Group: {trip.group.name}, Status: {trip.status}, Winner: {trip.is_winner}, Group ID: {trip.group.id})")
    else:
        accepted_group_trips = GroupItineraryOption.objects.none()
        print(f"[DEBUG] User {request.user.username} is not a member of any groups")
    
    # Prepare trip data with activities for each accepted trip
    from ai_implementation.models import ActivityResult
    import json as json_module
    
    accepted_trips_data = []
    for trip_option in accepted_group_trips:
        # Get activities for this trip
        activities = []
        if trip_option.search and trip_option.selected_activities:
            try:
                activity_ids = json_module.loads(trip_option.selected_activities)
                if activity_ids:
                    activities = list(ActivityResult.objects.filter(
                        search=trip_option.search,
                        external_id__in=activity_ids
                    )[:5])  # Limit to 5 activities for display
            except:
                pass
        
        accepted_trips_data.append({
            'option': trip_option,
            'activities': activities,
        })
    
    context = {
        'user_profile': user_profile,
        'saved_itineraries': saved_itineraries,
        'active_trips': active_trips,
        'user_groups': user_groups,
        'accepted_group_trips': accepted_trips_data,  # This is the list with 'option' and 'activities' keys
    }
    
    print(f"[DEBUG] Context - accepted_group_trips count: {len(accepted_trips_data)}")
    for trip_data in accepted_trips_data:
        print(f"[DEBUG]   - {trip_data['option'].title} with {len(trip_data['activities'])} activities")
    
    return render(request, 'accounts/dashboard.html', context)

def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('accounts:home')

@login_required
@require_http_methods(["POST"])
def create_itinerary(request):
    """Create a new itinerary"""
    form = ItineraryForm(request.POST)
    if form.is_valid():
        itinerary = form.save(commit=False)
        itinerary.user = request.user
        itinerary.save()
        return JsonResponse({'success': True, 'itinerary_id': itinerary.id})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def get_itineraries(request):
    """Get user's itineraries"""
    itineraries = Itinerary.objects.filter(user=request.user)
    data = []
    for itinerary in itineraries:
        data.append({
            'id': itinerary.id,
            'title': itinerary.title,
            'description': itinerary.description,
            'destination': itinerary.destination,
            'start_date': itinerary.start_date.strftime('%Y-%m-%d'),
            'end_date': itinerary.end_date.strftime('%Y-%m-%d'),
            'is_active': itinerary.is_active,
            'created_at': itinerary.created_at.strftime('%Y-%m-%d %H:%M')
        })
    return JsonResponse({'itineraries': data})

@login_required
@require_http_methods(["POST", "DELETE"])
def delete_itinerary(request, itinerary_id):
    """Delete a user's itinerary"""
    try:
        itinerary = Itinerary.objects.get(id=itinerary_id, user=request.user)
        itinerary_title = itinerary.title
        itinerary.delete()
        return JsonResponse({
            'success': True, 
            'message': f'Itinerary "{itinerary_title}" has been deleted successfully.'
        })
    except Itinerary.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Itinerary not found or you do not have permission to delete it.'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)
