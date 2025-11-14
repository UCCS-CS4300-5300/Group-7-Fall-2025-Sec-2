# GroupGo Accounts System

A Django-based user account management system for the GroupGo travel application that allows users to create accounts, manage their profiles, and save travel itineraries.

## Features

- **User Registration**: Create accounts with name, email, phone number, and password
- **User Authentication**: Secure login/logout functionality
- **Dashboard**: Personalized dashboard showing active trips and saved itineraries
- **Itinerary Management**: Create, save, and organize travel plans
- **Responsive Design**: Modern, mobile-friendly interface using Bootstrap

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd /Users/devonwhite/Desktop/Github/Group-7-Fall-2025-Sec-2
   ```

2. **Create & activate a virtual environment (recommended):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy the sample env file and update any secrets/API keys:**
   ```bash
   cp env.sample .env
   ```
   Leaving the AI/travel keys blank automatically enables local-only mock data.

5. **Run database migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser (optional, for admin access):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Access the application:**
   - Homepage: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Local Development Notes

- If `OPENAI_API_KEY` is not set, the AI workflows fall back to deterministic, privacy-safe heuristics so searches, consensus, and itinerary generation continue to work offline.
- External travel APIs (Duffel, Amadeus, hotel/activity providers) already provide mock data paths when keys are absent, so no vendor accounts are required to exercise the UI.
- `env.sample` sets `CELERY_TASK_ALWAYS_EAGER=True`, which runs Celery tasks synchronously and removes the need to install Redis locally. Override these values in `.env` if you want to test the full async stack.

## User Flow

The application follows the Gherkin scenario provided:

1. **Homepage**: Users land on the GroupGo homepage with navigation to Login/Sign Up
2. **Login/Sign Up Page**: Users can choose between existing login or new account creation
3. **Sign Up Process**: 
   - Fill in Name (First Name + Last Name)
   - Enter Email address
   - Provide Phone Number
   - Set Password
   - Submit form
4. **Dashboard**: After successful signup/login, users are redirected to their personalized dashboard featuring:
   - Options to plan a new trip
   - Section for saved itineraries
   - Section for active trips

## API Endpoints

- `GET /` - Homepage
- `GET /login/` - Login page
- `POST /login/` - Process login
- `GET /signup/` - Sign up page
- `POST /signup/` - Process signup
- `GET /dashboard/` - User dashboard (requires authentication)
- `POST /logout/` - Logout user
- `POST /api/create-itinerary/` - Create new itinerary
- `GET /api/get-itineraries/` - Get user's itineraries

## Database Models

### UserProfile
- Extends Django's built-in User model
- Stores additional user information (phone number)
- One-to-one relationship with User

### Itinerary
- Stores travel plans and itineraries
- Links to User via foreign key
- Fields: title, description, destination, start_date, end_date, is_active

## Testing the Gherkin Scenario

To test the provided Gherkin scenario:

1. Start the server: `python manage.py runserver`
2. Navigate to https://groupgo.decisiveonion.com/
3. Click "Sign Up" in the navigation
4. Fill in the form with:
   - Name: "Darth"
   - Email: "notdarthvader@aol.com"
   - Phone Number: "7195551525"
   - Password: "password"
5. Click "Submit"
6. Verify you're redirected to the dashboard
7. Confirm the dashboard shows:
   - Options to plan a new trip
   - Section for saved itineraries
   - Section for active trips

## Project Structure

```
groupgo/
├── accounts/                 # Django app for user accounts
│   ├── models.py            # Database models
│   ├── views.py             # View functions
│   ├── forms.py             # Django forms
│   ├── urls.py              # URL routing
│   ├── admin.py             # Admin configuration
│   └── templates/           # HTML templates
│       └── accounts/
│           ├── home.html
│           ├── login.html
│           ├── signup.html
│           └── dashboard.html
├── settings.py              # Django settings
├── urls.py                  # Main URL configuration
└── requirements.txt         # Python dependencies
```

## Security Features

- Password hashing using Django's built-in authentication
- CSRF protection on all forms
- Session-based authentication
- Input validation and sanitization
- SQL injection protection through Django ORM

## Future Enhancements

- Email verification for new accounts
- Password reset functionality
- Social media login integration
- Advanced itinerary sharing features
- Group trip planning capabilities
- Integration with travel APIs
