from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('api/create-itinerary/', views.create_itinerary, name='create_itinerary'),
    path('api/get-itineraries/', views.get_itineraries, name='get_itineraries'),
]
