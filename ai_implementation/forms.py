"""
Forms for AI Implementation
Handles user input for travel searches and AI-powered features.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TravelSearch, AIGeneratedItinerary


class TravelSearchForm(forms.ModelForm):
    """Form for creating a new travel search"""
    
    # Additional fields not in the model
    travel_method = forms.ChoiceField(
        choices=[
            ('flight', 'Flight'),
            ('car', 'Car'),
            ('train', 'Train'),
            ('bus', 'Bus'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        initial='flight'
    )
    
    activity_preferences = forms.MultipleChoiceField(
        choices=[
            ('museums', 'Museums & Culture'),
            ('outdoor', 'Outdoor Activities'),
            ('food', 'Food & Dining'),
            ('adventure', 'Adventure Sports'),
            ('shopping', 'Shopping'),
            ('nightlife', 'Nightlife'),
            ('relaxation', 'Relaxation & Spa'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    class Meta:
        model = TravelSearch
        fields = [
            'destination', 'origin', 'start_date', 'end_date',
            'adults', 'rooms', 'budget_min', 'budget_max',
            'accommodation_type', 'activity_categories'
        ]
        widgets = {
            'destination': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., New York, Paris, Tokyo'
            }),
            'origin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Los Angeles, LAX'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'adults': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '20'
            }),
            'rooms': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'budget_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimum budget',
                'step': '50'
            }),
            'budget_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum budget',
                'step': '50'
            }),
            'accommodation_type': forms.Select(
                choices=[
                    ('', 'Any'),
                    ('hotel', 'Hotel'),
                    ('resort', 'Resort'),
                    ('apartment', 'Apartment/Airbnb'),
                    ('hostel', 'Hostel'),
                    ('boutique', 'Boutique Hotel'),
                ],
                attrs={'class': 'form-control'}
            ),
            'activity_categories': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make origin explicitly optional (model allows blank, but form should too)
        self.fields['origin'].required = False
        # Make rooms optional with default
        self.fields['rooms'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')
        
        # Validate dates
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('End date must be after start date.')
            
            # Use timezone-aware date comparison
            today = timezone.now().date()
            if start_date < today:
                raise ValidationError('Start date cannot be in the past.')
            
            # Limit to reasonable trip duration (e.g., 30 days)
            if (end_date - start_date).days > 30:
                raise ValidationError('Trip duration cannot exceed 30 days.')
        
        # Validate budget
        if budget_min and budget_max:
            if budget_max < budget_min:
                raise ValidationError('Maximum budget must be greater than minimum budget.')
        
        # Process activity preferences
        if 'activity_preferences' in self.data:
            activity_prefs = self.data.getlist('activity_preferences')
            if activity_prefs:
                cleaned_data['activity_categories'] = ','.join(activity_prefs)
        
        return cleaned_data


class QuickSearchForm(forms.Form):
    """Simplified form for quick travel searches"""
    
    destination = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Where do you want to go?'
        })
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    adults = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=20,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'value': '1'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('End date must be after start date.')
            
            # Use timezone-aware date comparison
            today = timezone.now().date()
            if start_date < today:
                raise ValidationError('Start date cannot be in the past.')
        
        return cleaned_data


class GroupConsensusForm(forms.Form):
    """Form for generating group consensus from multiple preferences"""
    
    include_budget = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include budget analysis'
    )
    
    include_activities = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include activity recommendations'
    )
    
    include_accommodation = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include accommodation preferences'
    )
    
    prioritize_cost = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Prioritize lowest cost options'
    )


class ItineraryFeedbackForm(forms.Form):
    """Form for collecting user feedback on AI-generated results"""
    
    was_helpful = forms.ChoiceField(
        choices=[
            ('yes', 'Yes, very helpful'),
            ('somewhat', 'Somewhat helpful'),
            ('no', 'Not helpful'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Were these results helpful?'
    )
    
    feedback_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tell us how we can improve (optional)'
        }),
        label='Additional feedback'
    )


class SaveItineraryForm(forms.ModelForm):
    """Form for saving an AI-generated itinerary"""
    
    class Meta:
        model = AIGeneratedItinerary
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Give your itinerary a name'
            })
        }


class RefineSearchForm(forms.Form):
    """Form for refining search results"""
    
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum price'
        }),
        label='Maximum Price'
    )
    
    min_rating = forms.DecimalField(
        required=False,
        max_digits=3,
        decimal_places=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '4.0',
            'step': '0.1',
            'min': '0',
            'max': '5'
        }),
        label='Minimum Rating'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('ai_score', 'AI Recommendation'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('rating', 'Rating'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='ai_score',
        label='Sort By'
    )
    
    filter_type = forms.MultipleChoiceField(
        choices=[
            ('free_cancellation', 'Free Cancellation'),
            ('breakfast_included', 'Breakfast Included'),
            ('high_rating', 'Highly Rated (4+)'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Filters'
    )




