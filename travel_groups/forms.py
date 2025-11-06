from django import forms
from django.contrib.auth.models import User
from .models import TravelGroup, GroupMember, TravelPreference, TripPreference
from accounts.models import Itinerary

class CreateGroupForm(forms.ModelForm):
    """Form for creating a new travel group"""
    class Meta:
        model = TravelGroup
        fields = ['name', 'description', 'photo', 'password', 'max_members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter group name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe your group...'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Set a password for joining'}),
            'max_members': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 50}),
        }

class JoinGroupForm(forms.Form):
    """Form for joining a group using group ID and password"""
    group_id = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 8-character group code',
            'style': 'text-transform: uppercase;'
        }),
        help_text="Enter the 8-character group code"
    )
    password = forms.CharField(
        max_length=100,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter group password'
        }),
        help_text="Enter the group password"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        group_id = cleaned_data.get('group_id')
        password = cleaned_data.get('password')
        
        if group_id and password:
            group_id = group_id.upper()
            try:
                from .models import TravelGroup
                group = TravelGroup.objects.get(id__startswith=group_id)
                if group.password != password:
                    raise forms.ValidationError("Incorrect password for this group.")
                cleaned_data['group'] = group
            except TravelGroup.DoesNotExist:
                raise forms.ValidationError("Group not found. Please check the group code.")
        
        return cleaned_data

class SearchGroupForm(forms.Form):
    """Form for searching groups"""
    search_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by group name, destination, or description...'
        })
    )
    destination = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by destination...'
        })
    )

class TravelPreferenceForm(forms.ModelForm):
    """Form for updating travel preferences"""
    class Meta:
        model = TravelPreference
        fields = [
            'budget_range', 'accommodation_preference', 'activity_preferences',
            'dietary_restrictions', 'accessibility_needs', 'notes'
        ]
        widgets = {
            'budget_range': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., $500-1000'}),
            'accommodation_preference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hotel, Airbnb, Hostel, etc.'}),
            'activity_preferences': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What activities do you enjoy?'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any dietary restrictions or preferences?'}),
            'accessibility_needs': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any accessibility requirements?'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any additional notes or preferences?'}),
        }

class GroupSettingsForm(forms.ModelForm):
    """Form for updating group settings"""
    class Meta:
        model = TravelGroup
        fields = ['name', 'description', 'max_members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_members': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 50}),
        }

class TripPreferenceForm(forms.ModelForm):
    """Form for trip preferences input"""
    class Meta:
        model = TripPreference
        fields = [
            'start_date', 'end_date', 'destination', 'budget', 'travel_method', 
            'rental_car', 'accommodation_preference', 'activity_preferences',
            'dietary_restrictions', 'accessibility_needs', 'additional_notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter destination'}),
            'budget': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., $1700'}),
            'travel_method': forms.Select(attrs={'class': 'form-control'}),
            'rental_car': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accommodation_preference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hotel, Airbnb, etc.'}),
            'activity_preferences': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What activities do you want to do?'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any dietary restrictions?'}),
            'accessibility_needs': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any accessibility requirements?'}),
            'additional_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any additional notes or preferences?'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("End date must be after start date.")
        
        return cleaned_data


class ItineraryForm(forms.ModelForm):
    """Form for creating itineraries"""
    class Meta:
        model = Itinerary
        fields = ['title', 'description', 'destination', 'start_date', 'end_date', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Trip title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe your trip...'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Destination'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date must be after or equal to start date.")
        
        return cleaned_data
