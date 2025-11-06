# AI Implementation for GroupGo

## Overview

This module provides AI-powered travel search and recommendation capabilities for the GroupGo travel planning application. It integrates with OpenAI's API to provide intelligent consolidation of travel search results from multiple sources.

## Features

### 🤖 AI-Powered Search
- **Smart Flight Search**: Searches and ranks flight options using AI
- **Hotel Recommendations**: Provides personalized hotel suggestions
- **Activity Discovery**: Finds activities and tours matching group preferences
- **Consolidated Results**: AI analyzes and ranks all options together

### 👥 Group Consensus
- **Preference Analysis**: Analyzes multiple group members' preferences
- **Conflict Resolution**: Identifies areas of disagreement and suggests compromises
- **Smart Recommendations**: Generates consensus that works for everyone

### 📋 Itinerary Management
- **AI-Generated Descriptions**: Creates compelling itinerary descriptions
- **Budget Analysis**: Provides cost breakdowns and savings tips
- **Itinerary Saving**: Save and manage your favorite travel plans

## Installation

### 1. Install Required Packages

```bash
pip install -r requirements.txt
```

The following packages will be installed:
- `openai==1.12.0` - OpenAI API client
- `requests==2.31.0` - HTTP library for API calls
- `python-dotenv==1.0.0` - Environment variable management

### 2. Set Up Environment Variables

Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```
OPEN_AI_KEY=your-actual-openai-api-key
```

**Important**: You MUST set up an OpenAI API key for the AI features to work.
**Note**: The system uses the environment variable `OPEN_AI_KEY`.

Get your OpenAI API key from: https://platform.openai.com/api-keys

### 3. Run Migrations

```bash
python manage.py makemigrations ai_implementation
python manage.py migrate
```

### 4. Create Superuser (Optional)

To access the admin panel:

```bash
python manage.py createsuperuser
```

## Configuration

### OpenAI Configuration

The OpenAI integration is configured in `settings.py`:

```python
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = 'gpt-4-turbo-preview'
```

You can change the model to:
- `gpt-4-turbo-preview` (recommended, most capable)
- `gpt-4` (more expensive but very capable)
- `gpt-3.5-turbo` (faster and cheaper, less capable)

### Travel API Configuration

The module supports integration with various travel APIs:

#### Amadeus API (Flights)
Get credentials from: https://developers.amadeus.com/

```
AMADEUS_API_KEY=your-key
AMADEUS_API_SECRET=your-secret
```

**Note**: If API credentials are not configured, the system will use mock data for testing and development.

## Usage

### Basic Search Flow

1. **Navigate to AI Search**
   - Go to `/ai/` or click "AI Travel Search" in the navigation

2. **Enter Search Criteria**
   - Destination, dates, number of travelers
   - Budget range (optional)
   - Activity preferences (optional)

3. **View Results**
   - AI will search multiple sources
   - Results are consolidated and ranked
   - View AI recommendations with explanations

4. **Save Itinerary**
   - Select your preferred flight, hotel, and activities
   - Save as a complete itinerary

### Group Consensus Flow

1. **Group Members Submit Preferences**
   - Each member goes to their group page
   - Submits their trip preferences

2. **Generate Consensus**
   - Admin or any member can generate consensus
   - Go to: `/ai/group/<group_id>/consensus/generate/`

3. **View Consensus Results**
   - See areas of agreement
   - View suggested compromises
   - Identify conflicts and resolutions

4. **Search Based on Consensus**
   - Use the consensus to create a group search
   - Results will match the group's combined preferences

## API Structure

### Core Modules

#### `openai_service.py`
Handles all OpenAI API interactions:
- `consolidate_travel_results()` - Consolidates search results
- `generate_group_consensus()` - Creates group consensus
- `create_itinerary_description()` - Generates descriptions
- `answer_travel_question()` - Answers user questions

#### `api_connectors.py`
Manages connections to travel APIs:
- `FlightAPIConnector` - Flight searches
- `HotelAPIConnector` - Hotel searches
- `ActivityAPIConnector` - Activity searches
- `TravelAPIAggregator` - Combines all searches

#### Models
- `TravelSearch` - Stores search queries
- `ConsolidatedResult` - AI-consolidated results
- `FlightResult`, `HotelResult`, `ActivityResult` - Individual results
- `GroupConsensus` - Group preference analysis
- `AIGeneratedItinerary` - Saved itineraries
- `SearchHistory` - User search tracking

## URL Endpoints

```
/ai/                                    - Search home page
/ai/search/advanced/                    - Advanced search form
/ai/search/<id>/results/                - View search results
/ai/search/<id>/perform/                - Perform API search
/ai/group/<id>/consensus/generate/      - Generate group consensus
/ai/group/<id>/consensus/view/          - View consensus results
/ai/itineraries/                        - My saved itineraries
/ai/itinerary/<id>/                     - View itinerary details
/ai/search/<id>/save/                   - Save itinerary
```

## Mock Data

For development and testing without API keys, the system provides realistic mock data for:
- Flights (5 mock results per search)
- Hotels (8 mock results per search)
- Activities (10 mock results per search)

Mock data includes realistic:
- Prices and ratings
- Airline codes and hotel names
- Activity categories and descriptions

## Admin Interface

Access the admin panel at `/admin/` to:
- View all searches and results
- Monitor AI-generated content
- Track user search history
- Manage saved itineraries

## Testing

Run tests with:

```bash
python manage.py test ai_implementation
```

## Error Handling

The module includes comprehensive error handling:
- API timeouts are caught and logged
- Failed OpenAI calls return graceful defaults
- Mock data is used when APIs are unavailable
- User-friendly error messages

## Performance Considerations

- **Search Time**: 10-30 seconds per search (includes API calls and AI processing)
- **API Costs**: OpenAI API calls cost approximately $0.01-0.05 per search
- **Caching**: Results are saved to database for quick re-access
- **Rate Limiting**: Respects API rate limits

## Security

- API keys stored in environment variables (never in code)
- User authentication required for all endpoints
- CSRF protection on all forms
- Input validation on all forms

## Troubleshooting

### "OpenAI API key not found" Error
- Make sure you've set `OPENAI_API_KEY` in your environment variables or `.env` file
- Restart the Django development server after setting environment variables

### Mock Data Appearing Instead of Real Results
- This means API credentials are not configured
- The app will work with mock data for testing
- Configure real API keys in `.env` to get actual results

### Search Taking Too Long
- Normal search time is 10-30 seconds
- If longer, check your internet connection
- Check if API services are operational

### AI Recommendations Not Showing
- Check OpenAI API key is valid
- Check OpenAI API quota/billing
- Review logs for specific error messages

## Future Enhancements

Potential improvements:
- Real-time price tracking
- Email alerts for price drops
- Multi-city trip support
- Calendar integration
- Social sharing features
- Mobile app integration

## Support

For issues or questions:
1. Check this README
2. Review the inline code documentation
3. Check Django logs: `python manage.py runserver` output
4. Review OpenAI API documentation: https://platform.openai.com/docs

## License

This module is part of the GroupGo project and follows the same license.

