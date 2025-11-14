"""
OpenAI Service Module
Handles all interactions with the OpenAI API for consolidating and processing travel search results.
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from django.conf import settings


class OpenAIService:
    """Service class for interacting with OpenAI API"""
    
    def __init__(self):
        """Initialize OpenAI client with API key from environment or settings"""
        api_key = (
            os.environ.get('OPENAI_API_KEY')
            or os.environ.get('OPEN_AI_KEY')
            or getattr(settings, 'OPENAI_API_KEY', None)
        )
        if isinstance(api_key, str):
            api_key = api_key.strip()
        else:
            api_key = None
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4-turbo-preview')
        self.use_mock = not bool(api_key)
        self.client = None
        self._client_init_error = None
        if not self.use_mock:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as exc:
                self._client_init_error = str(exc)
                self.use_mock = True
                print(
                    f"OpenAI client initialization failed ({exc}). "
                    "Switching to deterministic mock mode so development can continue."
                )
        if self.use_mock:
            print(
                "OpenAI API key not found or client unavailable. Falling back to deterministic mock "
                "responses so AI features remain usable locally."
            )
    
    def consolidate_travel_results(
        self,
        flight_results: List[Dict[str, Any]],
        hotel_results: List[Dict[str, Any]],
        activity_results: List[Dict[str, Any]],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use OpenAI to consolidate and rank travel search results based on user preferences.
        
        Args:
            flight_results: List of flight search results
            hotel_results: List of hotel search results
            activity_results: List of activity search results
            user_preferences: Dictionary containing user/group preferences
            
        Returns:
            Dictionary containing consolidated and ranked results with AI recommendations
        """
        
        # Prepare the prompt for OpenAI
        prompt = self._create_consolidation_prompt(
            flight_results, hotel_results, activity_results, user_preferences
        )
        
        if self.use_mock:
            return self._mock_consolidation_response(
                flight_results, hotel_results, activity_results, user_preferences, error=self._client_init_error
            )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert travel planner AI assistant. Your job is to analyze "
                            "multiple travel options (flights, hotels, activities) and consolidate them "
                            "into a coherent, ranked recommendation based on user preferences. "
                            "Provide practical advice and explain your reasoning."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            return self._mock_consolidation_response(
                flight_results, hotel_results, activity_results, user_preferences, error=str(e)
            )
    
    def _create_consolidation_prompt(
        self,
        flights: List[Dict],
        hotels: List[Dict],
        activities: List[Dict],
        preferences: Dict
    ) -> str:
        """Create a detailed prompt for OpenAI to consolidate travel results"""
        
        prompt = f"""
Please analyze the following travel options and provide consolidated recommendations.

USER PREFERENCES:
{json.dumps(preferences, indent=2)}

FLIGHT OPTIONS ({len(flights)} results):
{json.dumps(flights[:10], indent=2)}  # Limit to top 10 to save tokens

HOTEL OPTIONS ({len(hotels)} results):
{json.dumps(hotels[:10], indent=2)}  # Limit to top 10

ACTIVITY OPTIONS ({len(activities)} results):
{json.dumps(activities[:10], indent=2)}  # Limit to top 10

Please provide a JSON response with the following structure:
{{
    "summary": "Brief overview of the best options considering all preferences",
    "recommended_flights": [
        {{
            "rank": 1,
            "flight_id": "id from original data",
            "reason": "Why this flight is recommended",
            "score": 95
        }}
    ],
    "recommended_hotels": [
        {{
            "rank": 1,
            "hotel_id": "id from original data",
            "reason": "Why this hotel is recommended",
            "score": 90
        }}
    ],
    "recommended_activities": [
        {{
            "rank": 1,
            "activity_id": "id from original data",
            "reason": "Why this activity is recommended",
            "score": 88
        }}
    ],
    "budget_analysis": {{
        "estimated_total": "Estimated total cost",
        "breakdown": "Cost breakdown",
        "savings_tips": "Tips for saving money"
    }},
    "itinerary_suggestions": [
        "Suggested day-by-day itinerary combining selected options"
    ],
    "warnings": ["Any concerns or warnings about the selections"]
}}

Rank items by how well they match the preferences, with scores from 0-100.
Include only the top 5 recommendations for each category.
"""
        return prompt
    
    def generate_three_itinerary_options(
        self,
        member_preferences: List[Dict[str, Any]],
        flight_results: List[Dict[str, Any]],
        hotel_results: List[Dict[str, Any]],
        activity_results: List[Dict[str, Any]],
        selected_dates: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate 3 different itinerary options for group voting.
        Each option balances member preferences differently.
        
        Args:
            member_preferences: List of preference dictionaries from group members
            flight_results: Available flight options
            hotel_results: Available hotel options
            activity_results: Available activity options
            selected_dates: Optional dict with start_date, end_date, duration_days
            
        Returns:
            Dictionary containing 3 different itinerary options with reasoning
        """
        
        budget_stats = self._calculate_budget_stats(member_preferences)
        budgets = budget_stats['values']
        min_budget = budget_stats['min']
        median_budget = budget_stats['median']
        max_budget = budget_stats['max']
        
        # Build date info string
        date_info = ""
        if selected_dates:
            date_info = f"""
SELECTED TRAVEL DATES:
- Start Date: {selected_dates.get('start_date')}
- End Date: {selected_dates.get('end_date')}
- Duration: {selected_dates.get('duration_days')} days

IMPORTANT: All flights and hotels MUST match these dates. Filter your selections to match this date range.
"""
        
        # Build individual member summary
        member_summary = "\n".join([
            f"- {pref.get('user', 'Member')}: Budget ${pref.get('budget', 'N/A')}, Destination: {pref.get('destination', 'N/A')}, Activities: {pref.get('activity_preferences', 'N/A')}"
            for pref in member_preferences
        ])
        
        prompt = f"""
Analyze these {len(member_preferences)} group members' travel preferences and create 3 DIFFERENT itinerary options for them to vote on.

{date_info}

MEMBER PREFERENCES SUMMARY:
{member_summary}

BUDGET ANALYSIS FROM ALL MEMBERS:
- Lowest Budget: ${min_budget:.2f}
- Median Budget: ${median_budget:.2f}
- Highest Budget: ${max_budget:.2f}

FULL GROUP MEMBER PREFERENCES (with detailed preferences):
{json.dumps(member_preferences, indent=2)}

AVAILABLE FLIGHTS (top 5):
{json.dumps(flight_results[:5], indent=2)}

AVAILABLE HOTELS (top 5):
{json.dumps(hotel_results[:5], indent=2)}

AVAILABLE ACTIVITIES (top 8):
{json.dumps(activity_results[:8], indent=2)}

CRITICAL REQUIREMENTS:
- YOU MUST consider ALL {len(member_preferences)} members' preferences, not just one person
- Each option must balance ALL members' destination, activity, and accommodation preferences
- Different members may have different budgets - find compromises that work for the group
- IMPORTANT: Different members want different destinations - USE DIFFERENT DESTINATIONS across the 3 options when possible
- Look at the "searched_destination" field in flights/hotels/activities to see which destination each option is for
- Option A, B, and C should ideally feature DIFFERENT destinations from different members' preferences

Create 3 distinct options with SPECIFIC BUDGET TARGETS AND DESTINATION VARIETY:

DESTINATION SELECTION STRATEGY:
- Each member wants a specific destination (see their preferences)
- Try to feature a DIFFERENT destination in each option (A, B, C) when members have different preferences
- For example: If Member 1 wants Rome and Member 2 wants Sicily, Option A could be Rome, Option B could be Sicily, Option C could be a third location or the best compromise
- Select flights/hotels/activities that match each chosen destination (use "searched_destination" field)

1. **Option A - Budget-Friendly**: Target the LOWEST budget (${min_budget:.2f})
   - Choose ONE destination that best fits this budget
   - Select the cheapest flight, hotel, and activities FOR THAT DESTINATION
   - Must fit within ${min_budget:.2f} budget
   - Explain which member's destination preference this option prioritizes
   
2. **Option B - Balanced**: Target the MEDIAN budget (${median_budget:.2f})
   - Choose a DIFFERENT destination from Option A (if multiple destinations available)
   - Balance between cost and quality FOR THAT DESTINATION
   - Must fit within ${median_budget:.2f} budget
   - Explain which member's destination preference this option prioritizes
   
3. **Option C - Premium**: Target the HIGHEST budget (${max_budget:.2f})
   - Choose a DIFFERENT destination from Options A and B (if multiple destinations available)
   - Select the best quality flight, hotel, and activities FOR THAT DESTINATION
   - Can use up to ${max_budget:.2f} budget
   - Explain which member's destination preference this option prioritizes

For EACH option, provide a JSON response with this structure:
{{
    "options": [
        {{
            "option_letter": "A",
            "title": "Budget-Friendly Adventure",
            "description": "Detailed 2-3 sentence description of this option",
            "selected_flight_id": "MUST be exact 'id' field from AVAILABLE FLIGHTS above",
            "selected_hotel_id": "MUST be exact 'id' field from AVAILABLE HOTELS above",
            "selected_activity_ids": ["MUST be exact 'id' fields from AVAILABLE ACTIVITIES above"],
            "estimated_total_cost": 2500.00,
            "cost_per_person": 1250.00,
            "ai_reasoning": "Detailed explanation of why this combination works for the ENTIRE group, mentioning ALL members",
            "compromise_explanation": "How this option balances ALL {len(member_preferences)} members' preferences - specifically mention each member by name and their key preferences that are addressed",
            "pros": ["Advantage 1", "Advantage 2", "Advantage 3"],
            "cons": ["Trade-off 1", "Trade-off 2"]
        }},
        {{
            "option_letter": "B",
            "title": "Best All-Around Experience",
            "description": "...",
            ...
        }},
        {{
            "option_letter": "C",
            "title": "Premium Luxury Package",
            "description": "...",
            ...
        }}
    ],
    "voting_guidance": "Brief note on how members should consider their vote",
    "consensus_summary": "What all options have in common (unanimous preferences)"
}}

CRITICAL REMINDERS:
- ONLY use IDs that appear in the "AVAILABLE FLIGHTS", "AVAILABLE HOTELS", and "AVAILABLE ACTIVITIES" sections above
- DO NOT make up or create new IDs - copy the exact "id" field from the results provided
- If you select a hotel with id "hotel_rome_123", that EXACT ID must exist in the AVAILABLE HOTELS list
- In your ai_reasoning and compromise_explanation, explicitly mention how you incorporated EACH member's preferences
- If destinations differ among members, explain how you chose a compromise location or activities
- If activity preferences differ, explain how you selected activities that appeal to multiple members
- Show that you considered ALL {len(member_preferences)} members, not just the member with the strongest preferences
- Each option's total cost should reflect its budget tier (lowest/median/highest)

Make each option genuinely different in cost but similar in how well it serves ALL members!
"""
        
        # Log budget analysis for debugging
        print(f"\n💰 BUDGET ANALYSIS:")
        print(f"   All member budgets: {budgets}")
        print(f"   Min Budget: ${min_budget:.2f}")
        print(f"   Median Budget: ${median_budget:.2f}")
        print(f"   Max Budget: ${max_budget:.2f}")
        print(f"\n📋 MEMBER PREFERENCES:")
        for i, pref in enumerate(member_preferences, 1):
            print(f"   {i}. {pref.get('user')}: ${pref.get('budget')} - {pref.get('destination')} - {pref.get('activity_preferences', '')[:50]}...")
        
        if self.use_mock:
            return self._mock_itinerary_options(
                member_preferences,
                flight_results,
                hotel_results,
                activity_results,
                budget_stats,
                selected_dates,
                error=self._client_init_error
            )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert group travel coordinator AI. Your job is to create "
                            "3 distinct itinerary options that consider ALL group members equally. "
                            "CRITICAL: You must balance ALL members' preferences (destinations, activities, accommodations) "
                            "in EVERY option, not just focus on one person. The three options differ by budget level "
                            "(lowest/median/highest from the group), but ALL must satisfy everyone's preferences as much as possible. "
                            "Each option should explain which member preferences are prioritized and how compromises work for the group."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,  # Higher creativity for variety
                max_tokens=2500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error generating itinerary options: {str(e)}")
            return self._mock_itinerary_options(
                member_preferences,
                flight_results,
                hotel_results,
                activity_results,
                budget_stats,
                selected_dates,
                error=str(e)
            )
    
    def generate_group_consensus(self, member_preferences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple group members' preferences and generate a consensus.
        
        Args:
            member_preferences: List of preference dictionaries from group members
            
        Returns:
            Dictionary containing consensus preferences and recommendations
        """
        
        prompt = f"""
Analyze the following travel preferences from {len(member_preferences)} group members and find the best consensus.

GROUP MEMBER PREFERENCES:
{json.dumps(member_preferences, indent=2)}

Please provide a JSON response with:
{{
    "consensus_preferences": {{
        "destination": "Most agreed upon or best compromise destination",
        "date_range": "Optimal date range considering all preferences",
        "budget_range": "Budget range that works for everyone",
        "accommodation_type": "Best accommodation type for the group",
        "activities": ["Activities that most members would enjoy"],
        "dietary_accommodations": ["Dietary restrictions to consider"],
        "accessibility_needs": ["Accessibility requirements to consider"]
    }},
    "compromise_areas": [
        {{
            "aspect": "What aspect requires compromise",
            "options": ["Possible compromise solutions"],
            "recommendation": "Best compromise solution"
        }}
    ],
    "unanimous_preferences": ["Things everyone agrees on"],
    "conflicting_preferences": [
        {{
            "aspect": "What's in conflict",
            "members_affected": ["Members with this preference"],
            "suggestion": "How to resolve"
        }}
    ],
    "group_dynamics_notes": "Notes about group compatibility and suggestions"
}}
"""
        
        if self.use_mock:
            return self._mock_group_consensus(member_preferences, error=self._client_init_error)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert group travel coordinator. Your job is to analyze "
                            "multiple people's travel preferences and find the best consensus that "
                            "satisfies the group while being fair and practical."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error generating group consensus: {str(e)}")
            return self._mock_group_consensus(member_preferences, error=str(e))
    
    def create_itinerary_description(
        self,
        destination: str,
        activities: List[str],
        duration_days: int,
        preferences: Optional[Dict] = None
    ) -> str:
        """
        Generate a compelling itinerary description using OpenAI.
        
        Args:
            destination: Travel destination
            activities: List of selected activities
            duration_days: Number of days for the trip
            preferences: Optional user preferences
            
        Returns:
            Generated itinerary description
        """
        
        prefs_text = json.dumps(preferences, indent=2) if preferences else "No specific preferences"
        
        prompt = f"""
Create an engaging, detailed itinerary description for a {duration_days}-day trip to {destination}.

Activities to include: {', '.join(activities)}
User preferences: {prefs_text}

Generate a compelling description that:
1. Provides a day-by-day overview
2. Highlights unique experiences
3. Includes practical tips
4. Mentions dining and accommodation suggestions
5. Is enthusiastic but realistic

Keep it under 300 words and make it inspiring!
"""
        
        if self.use_mock:
            return self._fallback_itinerary_description(destination, activities, duration_days, preferences, error=self._client_init_error)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a creative travel writer who creates inspiring itinerary descriptions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating itinerary description: {str(e)}")
            return self._fallback_itinerary_description(destination, activities, duration_days, preferences, error=str(e))
    
    def answer_travel_question(self, question: str, context: Optional[Dict] = None) -> str:
        """
        Answer travel-related questions using OpenAI.
        
        Args:
            question: User's question
            context: Optional context about the trip/search
            
        Returns:
            AI-generated answer
        """
        
        context_text = json.dumps(context, indent=2) if context else "No specific context"
        
        prompt = f"""
Context: {context_text}

Question: {question}

Please provide a helpful, accurate answer to this travel question.
"""
        
        if self.use_mock:
            return self._fallback_answer(question, context, error=self._client_init_error)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a knowledgeable travel advisor. Provide accurate, helpful "
                            "information about travel destinations, planning, and logistics."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error answering question: {str(e)}")
            return self._fallback_answer(question, context, error=str(e))

    # ---------------------------------------------------------------------
    # Mock / fallback helpers
    # ---------------------------------------------------------------------

    def _mock_consolidation_response(
        self,
        flights: List[Dict[str, Any]],
        hotels: List[Dict[str, Any]],
        activities: List[Dict[str, Any]],
        preferences: Dict[str, Any],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate deterministic recommendations when OpenAI is unavailable."""
        def rank_items(items, id_field: str, fallback_fields: List[str], price_field: str, label: str):
            ranked = []
            sorted_items = sorted(
                items, key=lambda item: self._safe_number(item.get(price_field) or item.get('total_price') or item.get('price'))
            )[:5]
            for idx, item in enumerate(sorted_items, 1):
                identifier = self._extract_identifier(item, [id_field] + fallback_fields, f"{label.upper()}-{idx}")
                price_value = self._safe_number(item.get(price_field) or item.get('total_price') or item.get('price'))
                reason_bits = []
                if label == 'flight':
                    reason_bits.append(item.get('airline') or item.get('airline_name') or 'Flight')
                    reason_bits.append(f"${price_value:,.0f}" if price_value else "price not provided")
                elif label == 'hotel':
                    reason_bits.append(item.get('name', 'Hotel'))
                    rating = item.get('rating')
                    if rating:
                        reason_bits.append(f"{rating}★")
                    if price_value:
                        reason_bits.append(f"${price_value:,.0f} total")
                else:
                    reason_bits.append(item.get('name', 'Activity'))
                    if price_value:
                        reason_bits.append(f"${price_value:,.0f}")
                ranked.append({
                    'rank': idx,
                    f'{label}_id': identifier,
                    'reason': " • ".join(reason_bits),
                    'score': max(40, 95 - (idx - 1) * 8)
                })
            return ranked
        
        avg_flight = self._average_price(flights, 'price')
        avg_hotel = self._average_price(hotels, 'total_price') or self._average_price(hotels, 'price_per_night')
        avg_activity = self._average_price(activities, 'price')
        estimated_total = round(avg_flight + avg_hotel + avg_activity, 2)
        
        summary_destination = preferences.get('destination') or 'your chosen destination'
        summary = (
            f"Showing the best mock-ranked options for {preferences.get('adults', 1)} traveler(s) headed to "
            f"{summary_destination}. Prices are based on locally generated sample data."
        )
        
        warning_msg = "OpenAI API unavailable — using offline scoring logic."
        if error:
            warning_msg += f" (Reason: {error})"
        
        itinerary = []
        if flights and hotels:
            itinerary.append(
                f"Arrive via {flights[0].get('airline', 'top flight')} and stay at {hotels[0].get('name', 'a recommended hotel')}."
            )
        if activities:
            itinerary.append(f"Plan to enjoy {activities[0].get('name', 'a highlighted activity')} on day 2.")
        
        return {
            "summary": summary,
            "recommended_flights": rank_items(flights, 'id', ['external_id'], 'price', 'flight'),
            "recommended_hotels": rank_items(hotels, 'id', ['external_id'], 'total_price', 'hotel'),
            "recommended_activities": rank_items(activities, 'id', ['external_id'], 'price', 'activity'),
            "budget_analysis": {
                "estimated_total": estimated_total,
                "breakdown": {
                    "flights": avg_flight,
                    "hotels": avg_hotel,
                    "activities": avg_activity
                },
                "savings_tips": "Adjust mock search filters (dates, stops, star rating) to see different price tiers."
            },
            "itinerary_suggestions": itinerary,
            "warnings": [warning_msg]
        }
    
    def _mock_itinerary_options(
        self,
        member_preferences: List[Dict[str, Any]],
        flight_results: List[Dict[str, Any]],
        hotel_results: List[Dict[str, Any]],
        activity_results: List[Dict[str, Any]],
        budget_stats: Dict[str, Any],
        selected_dates: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create three deterministic itinerary options for local development."""
        tiers = [
            ('A', 'Budget-Friendly Adventure', budget_stats['min'], "Focuses on savings while keeping everyone involved."),
            ('B', 'Balanced Crowd-Pleaser', budget_stats['median'], "Balances cost, comfort, and activity variety."),
            ('C', 'Premium Experience', budget_stats['max'], "Leans into flexible budgets for maximum comfort.")
        ]
        
        flights_sorted = sorted(flight_results, key=lambda f: self._safe_number(f.get('price')))
        hotels_sorted = sorted(hotel_results, key=lambda h: self._safe_number(h.get('total_price') or h.get('price_per_night')))
        activities_sorted = sorted(activity_results, key=lambda a: self._safe_number(a.get('price')))
        
        members_summary = self._member_summary(member_preferences)
        options = []
        
        for idx, (option_letter, title, target_budget, description) in enumerate(tiers):
            flight = flights_sorted[min(idx, len(flights_sorted) - 1)] if flights_sorted else {}
            hotel = hotels_sorted[min(idx, len(hotels_sorted) - 1)] if hotels_sorted else {}
            acts = activities_sorted[idx * 2:(idx + 1) * 2] if activities_sorted else []
            
            flight_cost = self._safe_number(flight.get('price'))
            hotel_cost = self._safe_number(hotel.get('total_price') or hotel.get('price_per_night'))
            activity_cost = sum(self._safe_number(a.get('price')) for a in acts)
            total_cost = round(flight_cost + hotel_cost + activity_cost, 2)
            travelers = max(1, len(member_preferences) or 1)
            
            options.append({
                "option_letter": option_letter,
                "title": title,
                "description": description,
                "selected_flight_id": self._extract_identifier(flight, ['id', 'external_id'], f"MOCK-FLIGHT-{idx+1}"),
                "selected_hotel_id": self._extract_identifier(hotel, ['id', 'external_id'], f"MOCK-HOTEL-{idx+1}"),
                "selected_activity_ids": [
                    self._extract_identifier(act, ['id', 'external_id'], f"MOCK-ACT-{option_letter}-{i+1}")
                    for i, act in enumerate(acts)
                ],
                "estimated_total_cost": total_cost if total_cost else target_budget,
                "cost_per_person": round((total_cost if total_cost else target_budget) / travelers, 2),
                "ai_reasoning": (
                    f"Targets approximately ${target_budget:,.0f} by pairing {flight.get('airline', 'a flight')} "
                    f"with {hotel.get('name', 'a hotel')} and {len(acts)} curated activities."
                ),
                "compromise_explanation": (
                    f"Balances needs for {members_summary}. Each tier rotates destinations/price points "
                    "so every member sees their preferences reflected somewhere."
                ),
                "pros": [
                    "Uses locally generated sample data",
                    "No external API dependencies",
                    "Keeps all members involved in planning"
                ],
                "cons": [
                    "Exact availability not guaranteed",
                    "Prices are illustrative only"
                ]
            })
        
        voting_guidance = (
            "Have members rank Options A–C based on comfort with the estimated spend and highlighted activities. "
            "Because costs are mock values, treat them as relative comparisons instead of quotes."
        )
        consensus_summary = (
            f"All options include flights, lodging, and curated activities for {members_summary}. "
            "Dates are aligned with the selection provided." if selected_dates else
            f"Each option remains feasible for {members_summary} even without final dates."
        )
        
        notes = []
        if error:
            notes.append(f"AI provider unavailable ({error}); showing generated mock data instead.")
        if not (flight_results and hotel_results):
            notes.append("Consider running another search to expand the mock catalog for richer options.")
        
        response = {
            "options": options,
            "voting_guidance": voting_guidance,
            "consensus_summary": consensus_summary,
            "notes": notes
        }
        if error:
            response["error"] = error
        return response
    
    def _mock_group_consensus(
        self,
        member_preferences: List[Dict[str, Any]],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Produce a heuristic consensus summary when OpenAI cannot be reached."""
        budget_stats = self._calculate_budget_stats(member_preferences)
        destinations = [pref.get('destination') for pref in member_preferences if pref.get('destination')]
        destination = destinations[0] if destinations else "Flexible – decide as a group"
        
        activity_sets = []
        for pref in member_preferences:
            activities = pref.get('activity_preferences')
            if activities:
                if isinstance(activities, str):
                    activity_sets.extend([a.strip() for a in activities.split(',') if a.strip()])
                else:
                    activity_sets.extend(activities)
        top_activities = list(dict.fromkeys(activity_sets))[:4]
        
        unanimous = []
        if top_activities:
            unanimous.append("Group enjoys a mix of " + ", ".join(top_activities))
        
        conflicting = []
        if len(set(destinations)) > 1:
            conflicting.append({
                "aspect": "Destination",
                "members_affected": [pref.get('user', 'member') for pref in member_preferences],
                "suggestion": "Shortlist the most mentioned two cities and run a quick vote."
            })
        
        compromise = [
            {
                "aspect": "Budget",
                "options": [
                    f"Stick close to ${budget_stats['min']:,.0f}",
                    f"Aim for ${budget_stats['median']:,.0f}",
                    f"Splurge up to ${budget_stats['max']:,.0f}"
                ],
                "recommendation": f"Use the median budget (${budget_stats['median']:,.0f}) as the default voting threshold."
            }
        ]
        
        notes = "Keep communication async-friendly so everyone can react to mock itineraries."
        if error:
            notes += f" (AI note: {error})"
        
        return {
            "consensus_preferences": {
                "destination": destination,
                "date_range": "Based on each member's availability – align exact dates in the Trip Preferences form.",
                "budget_range": f"${budget_stats['min']:,.0f} - ${budget_stats['max']:,.0f}",
                "accommodation_type": "Modern mid-range hotel or rental that sleeps the full group.",
                "activities": top_activities or ["City highlights tour", "Group dinner"],
                "dietary_accommodations": list({
                    pref.get('dietary_restrictions')
                    for pref in member_preferences
                    if pref.get('dietary_restrictions')
                }),
                "accessibility_needs": list({
                    pref.get('accessibility_needs')
                    for pref in member_preferences
                    if pref.get('accessibility_needs')
                })
            },
            "compromise_areas": compromise,
            "unanimous_preferences": unanimous,
            "conflicting_preferences": conflicting,
            "group_dynamics_notes": notes
        }
    
    def _fallback_itinerary_description(
        self,
        destination: str,
        activities: List[str],
        duration_days: int,
        preferences: Optional[Dict],
        error: Optional[str] = None
    ) -> str:
        """Return a deterministic description for offline mode."""
        activity_text = ", ".join(activities) if activities else "your favorite activities"
        base = (
            f"Plan a {duration_days}-day escape to {destination}. "
            f"Day 1 focuses on arrivals and a relaxed neighborhood walk. "
            f"Mid-trip highlights include {activity_text}, while the final day reserves time "
            f"for last-minute shopping and farewells."
        )
        if preferences:
            base += " Preferences considered: " + ", ".join(
                f"{k}={v}" for k, v in preferences.items() if v
            )
        if error:
            base += f" (AI note: {error})"
        return base
    
    def _fallback_answer(
        self,
        question: str,
        context: Optional[Dict],
        error: Optional[str] = None
    ) -> str:
        """Provide a gentle reminder that the AI is offline with a helpful tip."""
        answer = (
            f"I can't reach the OpenAI API right now, but here are next steps for “{question}”: "
            "cross-check current travel advisories, compare at least two airlines/hotels, "
            "and keep the group's submitted preferences in mind."
        )
        if context:
            answer += f" Context I considered: {json.dumps(context)[:200]}."
        if error:
            answer += f" (AI note: {error})"
        return answer
    
    def _calculate_budget_stats(self, member_preferences: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse budgets from member preferences and provide summary statistics."""
        budgets = []
        for pref in member_preferences:
            raw_budget = pref.get('budget')
            if raw_budget is None:
                continue
            if isinstance(raw_budget, str):
                cleaned = raw_budget.replace('$', '').replace(',', '').strip()
            else:
                cleaned = raw_budget
            try:
                value = float(cleaned)
                if value > 0:
                    budgets.append(value)
            except (TypeError, ValueError):
                continue
        
        if budgets:
            budgets.sort()
            mid = len(budgets) // 2
            if len(budgets) % 2 == 0 and len(budgets) > 1:
                median_budget = (budgets[mid - 1] + budgets[mid]) / 2
            else:
                median_budget = budgets[mid]
            min_budget = budgets[0]
            max_budget = budgets[-1]
        else:
            budgets = []
            min_budget, median_budget, max_budget = 1000.0, 3000.0, 5000.0
        
        return {
            "values": budgets,
            "min": min_budget,
            "median": median_budget,
            "max": max_budget
        }
    
    def _safe_number(self, value: Any, default: float = 0.0) -> float:
        """Convert a value to float safely."""
        if value in (None, '', 'N/A'):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace('$', '').replace(',', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                return default
        return default
    
    def _average_price(self, items: List[Dict[str, Any]], field: str) -> float:
        values = [self._safe_number(item.get(field)) for item in items if self._safe_number(item.get(field))]
        return round(sum(values) / len(values), 2) if values else 0.0
    
    def _extract_identifier(self, item: Dict[str, Any], fields: List[str], fallback: str) -> str:
        for field in fields:
            if item.get(field):
                return str(item.get(field))
        return fallback
    
    def _member_summary(self, member_preferences: List[Dict[str, Any]]) -> str:
        names = [pref.get('user') for pref in member_preferences if pref.get('user')]
        if not names:
            return "the group"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return f"{', '.join(names[:-1])}, and {names[-1]}"

