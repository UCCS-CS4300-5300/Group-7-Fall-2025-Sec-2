# GroupGo - AI-Powered Group Travel Planning Platform

A Django-based collaborative travel planning application that helps groups organize trips together using AI-powered recommendations and democratic voting systems.

## Features

### User Management
- Secure registration and authentication
- Personal dashboards with active trips and saved itineraries
- Profile management

### Group Travel Planning
- Create/join password-protected travel groups
- Admin and member roles with capacity limits
- Submit preferences: budget, dates, destination, travel method, accommodations, activities, dietary needs

### AI-Powered Recommendations
- Smart search using OpenAI GPT-4o-mini
- Multi-source results: Flights (SerpAPI), Hotels (Makcorps), Activities (SerpAPI)
- Analyzes group preferences to find optimal compromises
- Generates multiple ranked itinerary options (A, B, C, etc.)

### Democratic Voting
- Vote on AI-generated itinerary options
- Real-time vote tracking and consensus detection
- Multiple voting rounds until unanimous approval

### Notifications & Weather
- Real-time notifications for invitations, submissions, and voting
- Email integration with background task processing
- Current weather and forecasts for destinations

### Responsive Design
- Mobile-friendly Bootstrap interface

## Technology Stack

- **Framework**: Django 5.2.8
- **Database**: SQLite (development), upgradable to PostgreSQL
- **AI/ML**: OpenAI GPT-4o-mini
- **Task Queue**: Celery 5.5.3 with Redis 7.0.1
- **Web Server**: Gunicorn 23.0.0 with WhiteNoise
- **APIs**: 
  - SerpAPI (Google Flights & Activities)
  - Makcorps API (Hotels)
  - Open-Meteo (Weather Forecasts)
- **Testing**: Coverage 7.12.0, Flake8 linting
- **Deployment**: Render.com

## Setup Instructions

### Prerequisites
- Python 3.12.3+, pip, Redis server
- API Keys: OpenAI, SerpAPI, Makcorps (see Environment Variables)

### Installation

```bash
# Clone and navigate
git clone https://github.com/UCCS-CS4300-5300/Group-7-Fall-2025-Sec-2.git
cd Group-7-Fall-2025-Sec-2/

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Set up database
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --no-input

# Optional: Seed test data
python manage.py seed_users --clear
python manage.py seed_groups --clear
python manage.py seed_prefs --clear

# Start services (in separate terminals)
redis-server
celery -A groupgo worker --loglevel=info
celery -A groupgo beat --loglevel=info
python manage.py runserver
```

**Access:** http://localhost:8000/ | **Admin:** http://localhost:8000/admin | **Production:** https://groupgo.me/

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# OpenAI API Configuration
OPEN_AI_KEY=sk-your-openai-api-key-here

# SerpApi Configuration (Google Flights & Activities)
SERP_API_KEY=your-serpapi-api-key-here

# Makcorps Hotel API Configuration
HOTEL_API_KEY=your-makcorps-api-key-here

# Email Configuration
EMAIL_BACKEND=groupgo.email_backend.MinimalConsoleEmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=noreply@groupgo.com

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

## User Flow

### Individual User Journey
1. **Sign Up/Login**: Create account or log in
2. **Dashboard**: View active trips and saved itineraries
3. **Create or Join Group**: Start a new travel group or join existing one
4. **Submit Preferences**: Enter travel dates, budget, destination, and preferences
5. **AI Search**: System searches and ranks travel options
6. **Vote on Options**: Review AI-generated itinerary options and vote
7. **Book Trip**: Once consensus is reached, proceed with booking

### Group Planning Flow
1. **Group Creation**: Admin creates group with name, description, and password
2. **Member Invitation**: Share group ID and password with travel companions
3. **Preference Collection**: Each member submits their individual preferences
4. **AI Analysis**: System analyzes all preferences to find optimal compromises
5. **Option Generation**: AI creates 3-5 itinerary options balancing everyone's needs
6. **Democratic Voting**: Members vote on presented options
7. **Consensus Detection**: System identifies if unanimous approval is achieved
8. **Iterative Process**: If no consensus, new options are generated and voting continues
9. **Final Selection**: Winning itinerary is saved to group dashboard

## API Endpoints

### Authentication
- `GET /accounts/login/` - Login page
- `POST /accounts/login/` - Process login
- `GET /accounts/signup/` - Sign up page
- `POST /accounts/signup/` - Process signup
- `POST /accounts/logout/` - Logout user
- `GET /accounts/dashboard/` - User dashboard (requires authentication)

### Travel Groups
- `GET /groups/` - List all groups
- `POST /groups/create/` - Create new group
- `GET /groups/<uuid:group_id>/` - View group details
- `POST /groups/<uuid:group_id>/join/` - Join a group
- `GET /groups/<uuid:group_id>/preferences/` - Submit trip preferences
- `POST /groups/<uuid:group_id>/preferences/submit/` - Save preferences

### AI Search & Recommendations
- `GET /ai/search/` - Travel search interface
- `POST /ai/search/execute/` - Execute AI-powered search
- `GET /ai/search/<uuid:search_id>/results/` - View search results
- `GET /ai/consensus/<uuid:group_id>/` - View group consensus analysis
- `GET /ai/voting/<uuid:group_id>/` - View voting options
- `POST /ai/voting/<uuid:group_id>/vote/` - Submit vote

### Itineraries
- `GET /accounts/itineraries/` - List user's itineraries
- `POST /accounts/itineraries/create/` - Create new itinerary
- `GET /accounts/itineraries/<uuid:itinerary_id>/` - View itinerary details

### Notifications
- Real-time notifications handled via Django signals and Celery tasks

## Testing

### Run Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
python manage.py test

# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report in htmlcov/
```

### Linting
```bash
# Run flake8 linting
flake8 .

# Generate HTML linting report
flake8 --format=html --htmldir=flake-report
```

### Manual Testing Checklist
1. **User Registration**: Create account with valid credentials
2. **Group Creation**: Create a travel group with password
3. **Group Joining**: Join group using group ID and password
4. **Preference Submission**: Submit complete trip preferences
5. **AI Search**: Execute search and verify results appear
6. **Voting**: Vote on presented itinerary options
7. **Consensus**: Verify unanimous votes are detected
8. **Notifications**: Check notification delivery on key events

## Deployment

The application is configured for deployment on Render.com:

```yaml
# render.yaml configuration
services:
  - type: web
    plan: free
    name: cs4300-groupgo
    buildCommand: "pip install -r requirements.txt && python manage.py migrate"
    startCommand: "gunicorn groupgo.wsgi:application"
```

### Production Considerations
- Configure PostgreSQL database (replace SQLite)
- Set up Redis instance for Celery
- Configure environment variables on hosting platform
- Set `DEBUG=False` in production
- Configure proper `ALLOWED_HOSTS`
- Set up SSL/HTTPS certificates
- Configure email SMTP for production
- Set up monitoring and logging

## Security Features

- **Authentication**: Django's built-in password hashing (PBKDF2)
- **CSRF Protection**: Enabled on all forms
- **Session Security**: HTTP-only cookies, secure session management
- **Input Validation**: Form validation and sanitization
- **SQL Injection Protection**: Django ORM parameterized queries
- **XSS Protection**: Template auto-escaping
- **Password Requirements**: Minimum length and complexity validation
- **Group Security**: Password-protected group access

## Key Features Implementation

### AI Integration
- **OpenAI GPT-4o-mini**: Used for natural language processing and recommendation generation
- **Smart Ranking**: AI analyzes and scores travel options based on group preferences
- **Consensus Building**: AI identifies compromises and generates balanced itinerary options
- **Contextual Understanding**: Processes member preferences to understand group dynamics

### API Integrations
- **SerpAPI**: Google Flights data for real-time flight search and activities/tours
- **Makcorps API**: Hotel search with pricing, ratings, and amenities
- **Open-Meteo**: Weather forecasts based on historical data and current conditions
- **Future-Ready**: Architecture supports adding more travel APIs (Amadeus, Duffel, etc.)

### Background Processing
- **Celery**: Asynchronous task execution for time-consuming operations
- **Redis**: Message broker for task queue management
- **Scheduled Tasks**: Celery Beat for periodic background jobs
- **Email Notifications**: Async email sending without blocking user experience

## Future Enhancements

- Email verification for new accounts
- Password reset functionality
- Social media login integration
- Advanced itinerary sharing features
- Group trip planning capabilities
- Travel API integrations (attractions, restaurants, etc.)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## AI Development Assistance

This project was developed with assistance from AI tools:

- **Cursor AI**: Used extensively throughout development for:
  - Feature planning and architecture design
  - Code implementation and debugging
  - Email verification system
  - Itinerary sharing functionality
  - Group trip planning logic
  - SerpAPI integration and error handling
  - Open-Meteo API weather integration
  - Trip voting system logic and UI
  - Dashboard itinerary presentation
  - Bug fixes and code optimization
  - Test case generation
  - Documentation improvement

The AI assistant helped accelerate development, identify edge cases, and implement best practices while maintaining code quality and consistency.

## Contact & Links

- **Production**: https://groupgo.me/
- **Repository**: https://github.com/UCCS-CS4300-5300/Group-7-Fall-2025-Sec-2
