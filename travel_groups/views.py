from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import TravelGroup, GroupMember, TravelPreference, GroupItinerary, TripPreference
from .forms import CreateGroupForm, JoinGroupForm, SearchGroupForm, TravelPreferenceForm, GroupSettingsForm, TripPreferenceForm, ItineraryForm
from accounts.models import Itinerary

@login_required
def group_list(request):
    """View to list all groups and search functionality"""
    form = SearchGroupForm(request.GET)
    groups = TravelGroup.objects.filter(is_active=True)
    
    if form.is_valid():
        search_query = form.cleaned_data.get('search_query')
        destination = form.cleaned_data.get('destination')
        
        if search_query:
            groups = groups.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(destination__icontains=search_query)
            )
        
        if destination:
            groups = groups.filter(destination__icontains=destination)
    
    # Add user membership status
    for group in groups:
        group.user_is_member = GroupMember.objects.filter(
            group=group, user=request.user
        ).exists()
    
    context = {
        'groups': groups,
        'form': form,
    }
    return render(request, 'travel_groups/group_list.html', context)

@login_required
def create_group(request):
    """View to create a new travel group"""
    if request.method == 'POST':
        form = CreateGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            
            # Add creator as admin member
            GroupMember.objects.create(
                group=group,
                user=request.user,
                role='admin'
            )
            
            messages.success(request, f'Group "{group.name}" created successfully!')
            messages.info(request, f'Your group code is: {group.get_unique_identifier()}')
            return redirect('travel_groups:group_detail', group_id=group.id)
    else:
        form = CreateGroupForm()
    
    return render(request, 'travel_groups/create_group.html', {'form': form})

@login_required
def group_detail(request, group_id):
    """View to show group details"""
    import json
    from datetime import date
    from ai_implementation.models import GroupConsensus, GroupItineraryOption, ItineraryVote, ActivityResult
    
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
        user_is_member = True
        user_role = membership.role
    except GroupMember.DoesNotExist:
        user_is_member = False
        user_role = None
    
    # Get group members
    members = GroupMember.objects.filter(group=group).select_related('user')
    
    # Get group itineraries
    group_itineraries = GroupItinerary.objects.filter(group=group).select_related('itinerary', 'added_by')
    
    # Get user's travel preferences if they're a member
    travel_preferences = None
    if user_is_member:
        try:
            travel_preferences = membership.travel_preferences
        except TravelPreference.DoesNotExist:
            pass
    
    # Get preference count for "Find Your Trip" button
    prefs_count = TripPreference.objects.filter(group=group, is_completed=True).count()
    
    # Check for active voting options
    voting_options = None
    user_vote = None
    votes_cast = 0
    voting_complete = False
    
    try:
        # Get latest consensus with options
        consensus = GroupConsensus.objects.filter(group=group, is_active=True).order_by('-created_at').first()
        
        if consensus:
            # Get the 3 voting options
            options = GroupItineraryOption.objects.filter(
                group=group,
                consensus=consensus
            ).select_related('selected_flight', 'selected_hotel')
            
            if options.exists():
                # Get activities for each option
                voting_options = []
                for option in options:
                    activity_ids = json.loads(option.selected_activities) if option.selected_activities else []
                    
                    # Get activities matching this option's destination
                    if option.search and activity_ids:
                        all_activities = ActivityResult.objects.filter(
                            search=option.search,
                            external_id__in=activity_ids
                        )
                        
                        # Filter activities to match option's destination
                        activities = []
                        for activity in all_activities:
                            try:
                                activity_raw = json.loads(activity.raw_data)
                                activity_destination = activity_raw.get('searched_destination', '')
                                
                                # If option has a destination, filter by it
                                if option.destination:
                                    if activity_destination == option.destination:
                                        activities.append(activity)
                                else:
                                    # No destination filtering - include all activities
                                    activities.append(activity)
                            except:
                                # If can't parse raw_data, include activity
                                activities.append(activity)
                        
                        # If no activities after filtering, fall back to showing all
                        if not activities and all_activities:
                            activities = list(all_activities)
                    else:
                        activities = []
                    
                    voting_options.append({
                        'option': option,
                        'activities': activities
                    })
                
                # Check if user has voted
                if user_is_member:
                    user_vote = ItineraryVote.objects.filter(group=group, user=request.user).first()
                
                # Get voting stats
                votes_cast = ItineraryVote.objects.filter(group=group).count()
                voting_complete = votes_cast >= members.count()
    except Exception as e:
        print(f"Error fetching voting options: {str(e)}")
        voting_options = None
    
    context = {
        'group': group,
        'members': members,
        'group_itineraries': group_itineraries,
        'user_is_member': user_is_member,
        'user_role': user_role,
        'travel_preferences': travel_preferences,
        'group_code': group.get_unique_identifier(),
        'user': request.user,  # Explicitly pass user for permission checks
        'prefs_count': prefs_count,  # For "Find Your Trip" button
        'voting_options': voting_options,  # For Trips tab voting display
        'user_vote': user_vote,
        'votes_cast': votes_cast,
        'voting_complete': voting_complete,
        'today': date.today(),  # For date picker minimum date
    }
    return render(request, 'travel_groups/group_detail.html', context)

@login_required
def join_group(request):
    """View to join a group using group code and password"""
    if request.method == 'POST':
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            
            # Check if user is already a member
            if GroupMember.objects.filter(group=group, user=request.user).exists():
                messages.warning(request, 'You are already a member of this group.')
                return redirect('travel_groups:group_detail', group_id=group.id)
            
            # Check if group is full
            if group.is_full:
                messages.error(request, 'This group is full and cannot accept new members.')
                return redirect('travel_groups:join_group')
            
            # Add user as member
            GroupMember.objects.create(
                group=group,
                user=request.user,
                role='member'
            )
            
            messages.success(request, f'Successfully joined group "{group.name}"!')
            return redirect('travel_groups:group_detail', group_id=group.id)
    else:
        form = JoinGroupForm()
    
    return render(request, 'travel_groups/join_group.html', {'form': form})

@login_required
def leave_group(request, group_id):
    """View to leave a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
        
        # Don't allow the creator to leave if they're the only admin
        if membership.role == 'admin':
            admin_count = GroupMember.objects.filter(group=group, role='admin').count()
            if admin_count == 1:
                messages.error(request, 'You cannot leave the group as you are the only admin. Transfer admin rights to another member first.')
                return redirect('travel_groups:group_detail', group_id=group.id)
        
        membership.delete()
        messages.success(request, f'You have left group "{group.name}".')
        return redirect('travel_groups:group_list')
        
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')

@login_required
def my_groups(request):
    """View to show user's groups"""
    user_groups = GroupMember.objects.filter(user=request.user).select_related('group')
    
    context = {
        'user_groups': user_groups,
    }
    return render(request, 'travel_groups/my_groups.html', context)

@login_required
def update_travel_preferences(request, group_id):
    """View to update travel preferences for a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    if request.method == 'POST':
        form = TravelPreferenceForm(request.POST)
        if form.is_valid():
            preferences, created = TravelPreference.objects.get_or_create(
                member=membership,
                defaults=form.cleaned_data
            )
            if not created:
                for field, value in form.cleaned_data.items():
                    setattr(preferences, field, value)
                preferences.save()
            
            # Update membership to indicate preferences are set
            membership.has_travel_preferences = True
            membership.save()
            
            messages.success(request, 'Your travel preferences have been updated!')
            return redirect('travel_groups:group_detail', group_id=group.id)
    else:
        try:
            preferences = membership.travel_preferences
            form = TravelPreferenceForm(instance=preferences)
        except TravelPreference.DoesNotExist:
            form = TravelPreferenceForm()
    
    context = {
        'group': group,
        'form': form,
    }
    return render(request, 'travel_groups/update_preferences.html', context)

@login_required
def group_settings(request, group_id):
    """View to manage group settings (admin only)"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is admin
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
        if membership.role != 'admin':
            messages.error(request, 'You do not have permission to manage this group.')
            return redirect('travel_groups:group_detail', group_id=group.id)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    if request.method == 'POST':
        form = GroupSettingsForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group settings updated successfully!')
            return redirect('travel_groups:group_detail', group_id=group.id)
    else:
        form = GroupSettingsForm(instance=group)
    
    context = {
        'group': group,
        'form': form,
    }
    return render(request, 'travel_groups/group_settings.html', context)

@login_required
def group_trip_management(request, group_id):
    """View for managing trips within a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    # Get group itineraries - ensure we get all trips linked to this group
    # Use select_related to avoid N+1 queries
    group_itineraries = GroupItinerary.objects.filter(
        group=group
    ).select_related('itinerary', 'added_by').order_by('-added_at')
    
    # Debug logging
    print(f"📋 Group '{group.name}' has {group_itineraries.count()} trips")
    for gi in group_itineraries:
        print(f"   - {gi.itinerary.title} (ID: {gi.itinerary.id}) added by {gi.added_by.username}")
    
    # Get user's personal itineraries for adding to group
    # Exclude itineraries already in this group
    existing_itinerary_ids = group_itineraries.values_list('itinerary_id', flat=True)
    user_itineraries = Itinerary.objects.filter(
        user=request.user
    ).exclude(
        id__in=existing_itinerary_ids
    )
    
    context = {
        'group': group,
        'group_itineraries': group_itineraries,
        'user_itineraries': user_itineraries,
        'user_role': membership.role,
        'user': request.user,  # Explicitly pass user for template comparison
    }
    return render(request, 'travel_groups/group_trip_management.html', context)

@login_required
@require_http_methods(["POST"])
def add_itinerary_to_group(request, group_id):
    """API endpoint to add an itinerary to a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    itinerary_id = request.POST.get('itinerary_id')
    
    try:
        itinerary = Itinerary.objects.get(id=itinerary_id, user=request.user)
        
        # Check if itinerary is already linked to this group
        if GroupItinerary.objects.filter(group=group, itinerary=itinerary).exists():
            return JsonResponse({'success': False, 'message': 'Itinerary is already linked to this group.'})
        
        # Create the link
        GroupItinerary.objects.create(
            group=group,
            itinerary=itinerary,
            added_by=request.user
        )
        
        return JsonResponse({'success': True, 'message': 'Itinerary added to group successfully!'})
        
    except Itinerary.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Itinerary not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

@login_required
@require_http_methods(["POST"])
def create_group_trip(request, group_id):
    """Create a new trip for the group"""
    from django.db import transaction
    
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'You are not a member of this group.'})
    
    form = ItineraryForm(request.POST)
    if form.is_valid():
        try:
            # Use atomic transaction to ensure both saves succeed
            with transaction.atomic():
                itinerary = form.save(commit=False)
                itinerary.user = request.user
                itinerary.save()
                
                # Link to group - this ensures trip appears in group
                group_itinerary = GroupItinerary.objects.create(
                    group=group,
                    itinerary=itinerary,
                    added_by=request.user,
                    is_approved=True  # Auto-approve trips created by members
                )
                
                print(f"✅ Created trip '{itinerary.title}' (ID: {itinerary.id}) for group '{group.name}'")
                print(f"✅ GroupItinerary link created (ID: {group_itinerary.id})")
            
            return JsonResponse({
                'success': True, 
                'itinerary_id': itinerary.id,
                'message': f'Trip "{itinerary.title}" created successfully!'
            })
        except Exception as e:
            print(f"❌ Error creating trip: {str(e)}")
            return JsonResponse({'success': False, 'errors': str(e)})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

@login_required
def collect_group_preferences(request, group_id):
    """Collect and process group preferences for API integration"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    # Get all members with their preferences
    members = GroupMember.objects.filter(group=group).select_related('user', 'travel_preferences')
    
    # Collect all preferences data
    preferences_data = []
    for member in members:
        if member.has_travel_preferences:
            try:
                prefs = member.travel_preferences
                preferences_data.append({
                    'user': member.user.username,
                    'budget_range': prefs.budget_range,
                    'accommodation': prefs.accommodation_preference,
                    'activities': prefs.activity_preferences,
                    'dietary': prefs.dietary_restrictions,
                    'accessibility': prefs.accessibility_needs,
                    'notes': prefs.notes
                })
            except TravelPreference.DoesNotExist:
                pass
    
    context = {
        'group': group,
        'members': members,
        'preferences_data': preferences_data,
        'total_members': members.count(),
        'members_with_preferences': len(preferences_data),
    }
    return render(request, 'travel_groups/collect_preferences.html', context)

@login_required
def add_trip_preferences(request, group_id):
    """View to add trip preferences for a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    if request.method == 'POST':
        form = TripPreferenceForm(request.POST)
        if form.is_valid():
            # Check if user already has preferences for this group
            trip_pref, created = TripPreference.objects.get_or_create(
                group=group,
                user=request.user,
                defaults=form.cleaned_data
            )
            
            if not created:
                # Update existing preferences
                for field, value in form.cleaned_data.items():
                    setattr(trip_pref, field, value)
                trip_pref.save()
            
            # Mark as completed
            trip_pref.is_completed = True
            trip_pref.save()
            
            messages.success(request, 'Preferences Saved!')
            return redirect('travel_groups:group_detail', group_id=group.id)
    else:
        # Try to get existing preferences
        try:
            trip_pref = TripPreference.objects.get(group=group, user=request.user)
            form = TripPreferenceForm(instance=trip_pref)
        except TripPreference.DoesNotExist:
            form = TripPreferenceForm()
    
    context = {
        'group': group,
        'form': form,
    }
    return render(request, 'travel_groups/add_trip_preferences.html', context)

@login_required
def view_group_trip_preferences(request, group_id):
    """View to display all group members' trip preferences"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    # Get all trip preferences for this group
    trip_preferences = TripPreference.objects.filter(group=group).select_related('user')
    
    # Get group members
    members = GroupMember.objects.filter(group=group).select_related('user')
    
    context = {
        'group': group,
        'trip_preferences': trip_preferences,
        'members': members,
    }
    return render(request, 'travel_groups/view_trip_preferences.html', context)


@login_required
@require_http_methods(["POST"])
def edit_group_trip(request, group_id, itinerary_id):
    """Edit a trip/itinerary in a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'You are not a member of this group.'})
    
    # Get the itinerary
    try:
        itinerary = Itinerary.objects.get(id=itinerary_id)
        
        # Check permissions: only admin or the owner can edit
        if membership.role != 'admin' and itinerary.user != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to edit this trip.'})
        
        # Update the itinerary
        itinerary.title = request.POST.get('title', itinerary.title)
        itinerary.description = request.POST.get('description', itinerary.description)
        itinerary.destination = request.POST.get('destination', itinerary.destination)
        
        # Update dates if provided
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date:
            itinerary.start_date = start_date
        if end_date:
            itinerary.end_date = end_date
        
        itinerary.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Trip "{itinerary.title}" has been updated successfully.'
        })
        
    except Itinerary.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Trip not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST", "GET"])
def delete_group_trip(request, group_id, itinerary_id):
    """Delete a trip/itinerary from a group"""
    group = get_object_or_404(TravelGroup, id=group_id)
    
    # Check if user is a member
    try:
        membership = GroupMember.objects.get(group=group, user=request.user)
    except GroupMember.DoesNotExist:
        messages.error(request, 'You are not a member of this group.')
        return redirect('travel_groups:group_list')
    
    # Get the group itinerary link
    try:
        group_itinerary = GroupItinerary.objects.get(
            group=group,
            itinerary_id=itinerary_id
        )
        
        # Check permissions: only admin or the person who added it can delete
        if membership.role != 'admin' and group_itinerary.added_by != request.user:
            messages.error(request, 'You do not have permission to delete this trip.')
            return redirect('travel_groups:group_detail', group_id=group.id)
        
        # Store trip title for message
        trip_title = group_itinerary.itinerary.title
        
        # Delete the link (not the itinerary itself, just the group connection)
        group_itinerary.delete()
        
        messages.success(request, f'Trip "{trip_title}" has been removed from the group.')
        
        # Return JSON if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Trip "{trip_title}" removed successfully.'})
        
        # Otherwise redirect back
        return redirect('travel_groups:group_trip_management', group_id=group.id)
        
    except GroupItinerary.DoesNotExist:
        messages.error(request, 'Trip not found in this group.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Trip not found'})
        
        return redirect('travel_groups:group_detail', group_id=group.id)