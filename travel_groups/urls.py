from django.urls import path
from . import views

app_name = 'travel_groups'

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('create/', views.create_group, name='create_group'),
    path('join/', views.join_group, name='join_group'),
    path('my-groups/', views.my_groups, name='my_groups'),
    path('<uuid:group_id>/', views.group_detail, name='group_detail'),
    path('<uuid:group_id>/leave/', views.leave_group, name='leave_group'),
    path('<uuid:group_id>/preferences/', views.update_travel_preferences, name='update_preferences'),
    path('<uuid:group_id>/settings/', views.group_settings, name='group_settings'),
    path('<uuid:group_id>/trips/', views.group_trip_management, name='group_trip_management'),
    path('<uuid:group_id>/add-itinerary/', views.add_itinerary_to_group, name='add_itinerary'),
    path('<uuid:group_id>/create-trip/', views.create_group_trip, name='create_group_trip'),
    path('<uuid:group_id>/edit-trip/<int:itinerary_id>/', views.edit_group_trip, name='edit_group_trip'),
    path('<uuid:group_id>/delete-trip/<int:itinerary_id>/', views.delete_group_trip, name='delete_group_trip'),
    path('<uuid:group_id>/collect-preferences/', views.collect_group_preferences, name='collect_preferences'),
    path('<uuid:group_id>/add-trip-preferences/', views.add_trip_preferences, name='add_trip_preferences'),
    path('<uuid:group_id>/view-trip-preferences/', views.view_group_trip_preferences, name='view_trip_preferences'),
]
