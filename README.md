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
   cd Group-7-Fall-2025-Sec-2/
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
   **IMPORTANT:** Always activate the virtual environment before running Django commands. You should see `(venv)` in your terminal prompt when it's activated.

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   **Note:** If you get "ModuleNotFoundError" errors, make sure your virtual environment is activated!

4. **Run database migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser (optional, for admin access):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server:**
   ```bash
   # Make sure venv is activated first!
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python manage.py runserver
   ```
   **Tip:** If you forget to activate the venv, Django will use your system Python and you'll get import errors. Always check that `(venv)` appears in your terminal prompt.

7. **Access the application:**
   - Homepage: https://groupgo.me/
   - Admin panel: https://groupgo.me/admin

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

## AI Documentation

- Cursor AI was used and assisted in the planning, implementation and correction of code for the following features: Email verification, Itinerary sharing, Group trip planning and helped plan and correct the code for SerpAPI integration. Cursor was also used to help implement the usage of Open-Meteo API to provide current weather and forcasted weather based on historcal data for a group's planned trip.
- Cursor has helped correct and adjust the logic for the trip voting functionality and the debugging of presenting selected itineraries on each users' dashboard.

