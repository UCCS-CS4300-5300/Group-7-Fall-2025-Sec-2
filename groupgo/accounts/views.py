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
    return render(request, 'accounts/home.html')

def login_view(request):
    """Login page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to find user by email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'accounts/login.html')

def signup_view(request):
    """Sign up page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(
                user=user,
                phone_number=form.cleaned_data['phone_number']
            )
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def dashboard_view(request):
    """User dashboard view"""
    user_profile = UserProfile.objects.get(user=request.user)
    saved_itineraries = Itinerary.objects.filter(user=request.user, is_active=False)
    active_trips = Itinerary.objects.filter(user=request.user, is_active=True)
    
    context = {
        'user_profile': user_profile,
        'saved_itineraries': saved_itineraries,
        'active_trips': active_trips,
    }
    return render(request, 'accounts/dashboard.html', context)

def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('home')

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
