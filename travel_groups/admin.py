from django.contrib import admin
from .models import TravelGroup, GroupMember, TravelPreference, GroupItinerary

@admin.register(TravelGroup)
class TravelGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'member_count', 'max_members', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'photo')
        }),
        ('Security', {
            'fields': ('password',)
        }),
        ('Group Settings', {
            'fields': ('max_members', 'is_active', 'created_by')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'role', 'has_travel_preferences', 'joined_at']
    list_filter = ['role', 'has_travel_preferences', 'joined_at']
    search_fields = ['user__username', 'user__email', 'group__name']
    readonly_fields = ['joined_at']

@admin.register(TravelPreference)
class TravelPreferenceAdmin(admin.ModelAdmin):
    list_display = ['member', 'budget_range', 'accommodation_preference', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['member__user__username', 'member__group__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(GroupItinerary)
class GroupItineraryAdmin(admin.ModelAdmin):
    list_display = ['group', 'itinerary', 'added_by', 'is_approved', 'added_at']
    list_filter = ['is_approved', 'added_at']
    search_fields = ['group__name', 'itinerary__title', 'added_by__username']
    readonly_fields = ['added_at']
