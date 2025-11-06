"""
OpenAI Service Module
Handles all interactions with the OpenAI API for consolidating and processing travel search results.
"""

import os
import json
import sys
from typing import List, Dict, Any, Optional
from openai import OpenAI
from django.conf import settings


class OpenAIService:
    """Service class for interacting with OpenAI API"""

    def __init__(self):
        """Initialize OpenAI client with API key from environment or settings"""
        api_key = os.environ.get(
            "OPENAI_API_KEY", getattr(settings, "OPENAI_API_KEY", None)
        )
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in environment "
                "variables or Django settings."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def _log_request_size(self, messages: List[Dict[str, str]], function_name: str):
        """
        Calculate and log the size of the OpenAI request in KB.

        Args:
            messages: List of message dictionaries being sent to OpenAI
            function_name: Name of the function making the request
        """
        # Convert messages to JSON string to get actual payload size
        messages_json = json.dumps(messages)
        size_bytes = sys.getsizeof(messages_json)
        size_kb = size_bytes / 1024

        print(
            f"📦 OpenAI Request Size [{function_name}]: {size_kb:.2f} KB ({size_bytes:,} bytes)"
        )

        # Also log character count which correlates to token count
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        print(
            f"   Total characters in messages: {total_chars:,} (~{total_chars//4} tokens estimated)"
        )

        return size_kb

    def consolidate_travel_results(
        self,
        flight_results: List[Dict[str, Any]],
        hotel_results: List[Dict[str, Any]],
        activity_results: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
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

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert travel planner AI assistant. Your job is to analyze "
                        "multiple travel options (flights, hotels, activities) and consolidate them "
                        "into a coherent, ranked recommendation based on user preferences. "
                        "Provide practical advice and explain your reasoning."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "consolidate_travel_results")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            # Parse the response
            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            return {
                "error": str(e),
                "flights": flight_results,
                "hotels": hotel_results,
                "activities": activity_results,
            }

    def _create_consolidation_prompt(
        self,
        flights: List[Dict],
        hotels: List[Dict],
        activities: List[Dict],
        preferences: Dict,
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
        selected_dates: Dict[str, Any] = None,
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

        # Calculate budget statistics from all members
        budgets = []
        for pref in member_preferences:
            budget_val = pref.get("budget", "0")
            budget_str = str(budget_val)  # Ensure it's a string for processing
            # Handle both string and numeric budgets, remove $ and commas
            if isinstance(budget_str, str):
                budget_str = budget_str.replace("$", "").replace(",", "").strip()
            try:
                budget = float(budget_str)
                if budget > 0:
                    budgets.append(budget)
            except (ValueError, TypeError):
                continue

        # Calculate min, median, max budgets
        if budgets:
            budgets.sort()
            min_budget = budgets[0]
            max_budget = budgets[-1]
            median_budget = (
                budgets[len(budgets) // 2]
                if len(budgets) > 0
                else sum(budgets) / len(budgets)
            )
        else:
            # Fallback if no budgets found
            min_budget = 1000
            median_budget = 3000
            max_budget = 5000

        # Build date info string
        date_info = ""
        if selected_dates:
            date_info = f"Dates: {selected_dates.get('start_date')} to {selected_dates.get('end_date')} ({selected_dates.get('duration_days')}d). Match these dates."

        # OPTIMIZATION: Summarize member preferences concisely
        member_summary = []
        for pref in member_preferences:
            activities = pref.get("activity_preferences", [])
            if isinstance(activities, list):
                activities = ",".join(activities[:2])  # First 2 only
            else:
                activities = str(activities)[:40]
            member_summary.append(
                f"{pref.get('user', 'M')}: ${pref.get('budget', '?')}, {pref.get('destination', '?')}, {activities}"
            )

        # OPTIMIZATION: Ultra-compact data - only critical fields
        flights_compact = [
            {
                "id": f.get("id"),
                "to": f.get("searched_destination", "")[:20],
                "$": f.get("total_amount"),
            }
            for f in flight_results[:5]
        ]

        hotels_compact = [
            {
                "id": h.get("id"),
                "name": h.get("name", "")[:25],
                "to": h.get("searched_destination", "")[:20],
                "$": h.get("price_per_night"),
            }
            for h in hotel_results[:5]
        ]

        activities_compact = [
            {
                "id": a.get("id"),
                "name": a.get("name", "")[:30],
                "to": a.get("searched_destination", "")[:20],
                "$": a.get("price"),
            }
            for a in activity_results[:6]
        ]

        prompt = f"""Analyze {len(member_preferences)} members' travel preferences. Create 3 itinerary options for voting.

{date_info}
MEMBERS: {member_summary}
BUDGETS: Low=${min_budget:.2f}, Med=${median_budget:.2f}, High=${max_budget:.2f}

DATA:
{json.dumps(member_preferences, indent=2)}
{json.dumps(flight_results[:5], indent=2)}
{json.dumps(hotel_results[:5], indent=2)}
{json.dumps(activity_results[:8], indent=2)}

REQUIREMENTS:
- Balance ALL {len(member_preferences)} members' preferences
- Use DIFFERENT destinations per option when possible (check "searched_destination" field)
- Option A: ${min_budget:.2f} budget, cheapest choices for ONE destination
- Option B: ${median_budget:.2f} budget, balanced quality, DIFFERENT destination
- Option C: ${max_budget:.2f} budget, premium quality, DIFFERENT destination
- Explain which member's destination each option prioritizes

JSON OUTPUT:
{{"options":[{{"option_letter":"A","title":"...","description":"1-2 sentences","selected_flight_id":"exact id","selected_hotel_id":"exact id","selected_activity_ids":["exact ids"],"estimated_total_cost":0.00,"cost_per_person":0.00,"ai_reasoning":"Why this works for ALL members","compromise_explanation":"How this addresses EACH member by name","pros":["...","...","..."],"cons":["...","..."]}},{{"option_letter":"B",...}},{{"option_letter":"C",...}}],
"voting_guidance":"...","consensus_summary":"..."}}

CRITICAL: Use ONLY exact IDs from provided data. Mention ALL {len(member_preferences)} members in reasoning. Match costs to budget tiers."""

        # Log budget analysis for debugging
        print(f"\n💰 BUDGET ANALYSIS:")
        print(f"   All member budgets: {budgets}")
        print(f"   Min Budget: ${min_budget:.2f}")
        print(f"   Median Budget: ${median_budget:.2f}")
        print(f"   Max Budget: ${max_budget:.2f}")
        print(f"\n📋 MEMBER PREFERENCES:")
        for i, pref in enumerate(member_preferences, 1):
            print(
                f"   {i}. {pref.get('user')}: ${pref.get('budget')} - {pref.get('destination')} - {pref.get('activity_preferences', '')[:50]}..."
            )

        try:
            messages = [
                {
                    "role": "system",
                    "content": "Travel AI: Create 3 itinerary options balancing all group preferences. Return valid JSON matching exact structure.",
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "generate_three_itinerary_options")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Reduced for more consistent results
                max_tokens=1500,  # Increased slightly for detailed responses
                response_format={"type": "json_object"},
                timeout=90,  # Increased timeout to 90 seconds
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error generating itinerary options: {str(e)}")
            return {
                "error": str(e),
                "options": [],
                "note": "Unable to generate options due to error",
            }

    def generate_group_consensus(
        self, member_preferences: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert group travel coordinator. Your job is to analyze "
                        "multiple people's travel preferences and find the best consensus that "
                        "satisfies the group while being fair and practical."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "generate_group_consensus")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error generating group consensus: {str(e)}")
            return {
                "error": str(e),
                "consensus_preferences": {},
                "note": "Unable to generate consensus due to error",
            }

    def create_itinerary_description(
        self,
        destination: str,
        activities: List[str],
        duration_days: int,
        preferences: Optional[Dict] = None,
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

        prefs_text = (
            json.dumps(preferences, indent=2)
            if preferences
            else "No specific preferences"
        )

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

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a creative travel writer who creates inspiring itinerary descriptions.",
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "generate_itinerary_description")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error generating itinerary description: {str(e)}")
            return f"Explore {destination} over {duration_days} days with exciting activities including {', '.join(activities)}."

    def answer_travel_question(
        self, question: str, context: Optional[Dict] = None
    ) -> str:
        """
        Answer travel-related questions using OpenAI.

        Args:
            question: User's question
            context: Optional context about the trip/search

        Returns:
            AI-generated answer
        """

        context_text = (
            json.dumps(context, indent=2) if context else "No specific context"
        )

        prompt = f"""
Context: {context_text}

Question: {question}

Please provide a helpful, accurate answer to this travel question.
"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a knowledgeable travel advisor. Provide accurate, helpful "
                        "information about travel destinations, planning, and logistics."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "answer_travel_question")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Error answering question: {str(e)}")
            return "I apologize, but I'm unable to answer that question at the moment. Please try again later."
