from django.contrib import admin
from .models import Trip, User, Submission, PreferenceSubmission

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'trip']
    list_filter = ['trip']
    search_fields = ['name', 'email']

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'trip', 'submitted', 'submitted_at']
    list_filter = ['submitted', 'submitted_at', 'trip']
    search_fields = ['user__name', 'trip__name']

@admin.register(PreferenceSubmission)
class PreferenceSubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission', 'accommodation_type', 'transportation_preference', 'created_at']
    list_filter = ['accommodation_type', 'transportation_preference', 'created_at']
    search_fields = ['submission__user__name', 'submission__trip__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('submission',)
        }),
        ('Budget', {
            'fields': ('budget_min', 'budget_max')
        }),
        ('Activities', {
            'fields': ('preferred_activities', 'avoid_activities')
        }),
        ('Accommodation & Transportation', {
            'fields': ('accommodation_type', 'transportation_preference')
        }),
        ('Food Preferences', {
            'fields': ('dietary_restrictions', 'cuisine_preferences')
        }),
        ('Additional Info', {
            'fields': ('additional_notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
