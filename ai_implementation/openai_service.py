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
            f"[INFO] OpenAI Request Size [{function_name}]: {size_kb:.2f} KB ({size_bytes:,} bytes)"
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
        unique_destinations: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate 5-8 different itinerary options for group voting.
        Each option balances member preferences differently.

        Args:
            member_preferences: List of preference dictionaries from group members
            flight_results: Available flight options
            hotel_results: Available hotel options
            activity_results: Available activity options
            selected_dates: Optional dict with start_date, end_date, duration_days

        Returns:
            Dictionary containing 5-8 different itinerary options with reasoning
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

        # Extract unique destinations if not provided
        if unique_destinations is None:
            unique_destinations = list(set([
                pref.get("destination", "").strip()
                for pref in member_preferences
                if pref.get("destination", "").strip()
            ]))
        
        # Build date info string
        date_info = ""
        if selected_dates:
            date_info = f"Dates: {selected_dates.get('start_date')} to {selected_dates.get('end_date')} ({selected_dates.get('duration_days')}d). Match these dates."
        
        # Build destination requirement string
        destination_requirement = ""
        if unique_destinations and len(unique_destinations) > 1:
            min_options_per_dest = 3
            total_min_options = len(unique_destinations) * min_options_per_dest
            destination_requirement = f"\n\n🚨 CRITICAL DESTINATION DISTRIBUTION REQUIREMENT 🚨\n- You have {len(unique_destinations)} DIFFERENT destinations: {', '.join(unique_destinations)}\n- You MUST create at least {min_options_per_dest} options for EACH destination\n- DO NOT create all options for the same destination - you MUST distribute across ALL destinations\n- Example: If destinations are [Paris, Tokyo], create at least 3 options for Paris AND at least 3 options for Tokyo\n- Each destination's options should vary in budget (budget, balanced, premium)\n- Use the 'searched_destination' field in flight/hotel data to match destinations correctly\n- Minimum total: {total_min_options} options (at least {min_options_per_dest} per destination), maximum: 8 total"
        elif unique_destinations and len(unique_destinations) == 1:
            # Single destination - just ensure variety
            destination_requirement = f"\n- Create 5-8 diverse options for {unique_destinations[0]} with different budget tiers"

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

        prompt = f"""Analyze {len(member_preferences)} members' travel preferences. Create 5-8 diverse itinerary options for voting.

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
{destination_requirement}
- Create 5-8 DIVERSE options with different destinations, budgets, and styles
- CRITICAL: If there are multiple unique destinations, you MUST create options for EACH destination - do not put all options in one destination
- Use DIFFERENT destinations per option when multiple destinations exist (check "searched_destination" field in flight/hotel data)
- Vary budgets: some at ${min_budget:.2f}, some at ${median_budget:.2f}, some at ${max_budget:.2f}
- Include options that prioritize different members' preferences
- Explain which member's destination each option prioritizes

JSON OUTPUT:
{{"options":[{{"option_letter":"A","title":"...","description":"1-2 sentences","intended_destination":"exact destination name from searched_destination field","selected_flight_id":"exact id","selected_hotel_id":"exact id","selected_activity_ids":["exact ids"],"estimated_total_cost":0.00,"cost_per_person":0.00,"ai_reasoning":"Why this works for ALL members","compromise_explanation":"How this addresses EACH member by name","pros":["...","...","..."],"cons":["...","..."]}},{{"option_letter":"B",...}},{{"option_letter":"C",...}},{{"option_letter":"D",...}},{{"option_letter":"E",...}},{{"option_letter":"F",...}},{{"option_letter":"G",...}},{{"option_letter":"H",...}}],
"voting_guidance":"...","consensus_summary":"..."}}

CRITICAL: Generate 5-8 options (use letters A-H). Use ONLY exact IDs from provided data. Mention ALL {len(member_preferences)} members in reasoning. Vary budgets and destinations. {destination_requirement}"""

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
            system_message = "Travel AI: Create 5-8 diverse itinerary options balancing all group preferences. "
            if unique_destinations and len(unique_destinations) > 1:
                system_message += f"CRITICAL: You have {len(unique_destinations)} different destinations ({', '.join(unique_destinations)}). You MUST create options for EACH destination - do not put all options in one destination. "
            system_message += "Return valid JSON matching exact structure."
            
            messages = [
                {
                    "role": "system",
                    "content": system_message,
                },
                {"role": "user", "content": prompt},
            ]

            # Log request size
            self._log_request_size(messages, "generate_three_itinerary_options")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Reduced for more consistent results
                max_tokens=2000,  # Increased for detailed responses
                response_format={"type": "json_object"},
                timeout=180,  # Increased timeout to 90 seconds
            )

            content = response.choices[0].message.content

            # Try to parse JSON, with fallback cleaning
            try:
                result = json.loads(content)
            except json.JSONDecodeError as json_error:
                print(f"JSON parse error: {str(json_error)}")
                print(f"Error at line {json_error.lineno}, column {json_error.colno}")
                print(f"Response content length: {len(content)}")
                print(f"Response content (first 1000 chars):\n{content[:1000]}")
                if len(content) > 1000:
                    print(f"Response content (last 500 chars):\n{content[-500:]}")

                # Try to fix common JSON issues
                try:
                    # Remove markdown code blocks if present
                    cleaned_content = content
                    if "```json" in cleaned_content:
                        cleaned_content = (
                            cleaned_content.split("```json")[1].split("```")[0].strip()
                        )
                    elif "```" in cleaned_content:
                        cleaned_content = (
                            cleaned_content.split("```")[1].split("```")[0].strip()
                        )

                    # Try parsing the cleaned content first
                    try:
                        result = json.loads(cleaned_content)
                        print("✅ Successfully parsed after removing markdown")
                    except json.JSONDecodeError as inner_error:
                        print(
                            f"Still failed after markdown removal: {str(inner_error)}"
                        )
                        # If that fails, try to extract JSON object using a more robust method
                        import re

                        # Find the first { and try to match balanced braces
                        start_idx = cleaned_content.find("{")
                        if start_idx != -1:
                            # Count braces to find the matching closing brace
                            brace_count = 0
                            end_idx = start_idx
                            for i in range(start_idx, len(cleaned_content)):
                                if cleaned_content[i] == "{":
                                    brace_count += 1
                                elif cleaned_content[i] == "}":
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end_idx = i + 1
                                        break

                            if brace_count == 0:
                                json_str = cleaned_content[start_idx:end_idx]
                                # Try to fix common issues in the extracted JSON
                                # Fix trailing commas before closing braces/brackets
                                json_str = re.sub(r",\s*}", "}", json_str)
                                json_str = re.sub(r",\s*]", "]", json_str)
                                # Try parsing
                                try:
                                    result = json.loads(json_str)
                                    print(
                                        "✅ Successfully extracted and parsed JSON using balanced brace matching"
                                    )
                                except json.JSONDecodeError as parse_error:
                                    print(
                                        f"Failed to parse extracted JSON: {str(parse_error)}"
                                    )
                                    print(
                                        f"Extracted JSON (first 500 chars): {json_str[:500]}"
                                    )
                                    return self._build_fallback_itinerary_options(
                                        member_preferences,
                                        flight_results,
                                        hotel_results,
                                        activity_results,
                                        selected_dates,
                                        str(json_error),
                                    )
                            else:
                                print("Could not find balanced braces in response")
                                return self._build_fallback_itinerary_options(
                                    member_preferences,
                                    flight_results,
                                    hotel_results,
                                    activity_results,
                                    selected_dates,
                                    str(json_error),
                                )
                        else:
                            print("Could not find opening brace in response")
                            return self._build_fallback_itinerary_options(
                                member_preferences,
                                flight_results,
                                hotel_results,
                                activity_results,
                                selected_dates,
                                str(json_error),
                            )
                except Exception as fix_error:
                    print(f"Failed to fix JSON: {str(fix_error)}")
                    import traceback

                    print(traceback.format_exc())
                    return self._build_fallback_itinerary_options(
                        member_preferences,
                        flight_results,
                        hotel_results,
                        activity_results,
                        selected_dates,
                        str(json_error),
                    )

            return result

        except Exception as e:
            print(f"Error generating itinerary options: {str(e)}")
            import traceback

            print(traceback.format_exc())
            raise

    def _build_fallback_itinerary_options(
        self,
        member_preferences: List[Dict[str, Any]],
        flight_results: List[Dict[str, Any]],
        hotel_results: List[Dict[str, Any]],
        activity_results: List[Dict[str, Any]],
        selected_dates: Optional[Dict[str, Any]],
        error_message: str,
    ) -> Dict[str, Any]:
        """Create deterministic itinerary options when AI JSON parsing fails."""

        letters = list("ABCDEFGH")
        group_size = max(len(member_preferences), 1)
        duration_days_raw = 0
        if selected_dates:
            duration_days_raw = (
                selected_dates.get("duration_days")
                or selected_dates.get("duration")
                or selected_dates.get("nights")
                or 0
            )
        duration_days = int(self._safe_float(duration_days_raw, 4) or 4)
        if duration_days <= 0:
            duration_days = 4

        def destination_for_option(
            flight: Dict[str, Any], hotel: Dict[str, Any], member_index: int
        ) -> str:
            candidates = [
                flight.get("searched_destination") if flight else None,
                flight.get("destination") if flight else None,
                hotel.get("searched_destination") if hotel else None,
                hotel.get("destination") if hotel else None,
            ]
            if member_preferences:
                pref = member_preferences[member_index % len(member_preferences)]
                candidates.append(pref.get("destination"))
            for candidate in candidates:
                if candidate:
                    return candidate
            return "Flexible Destination"

        max_options = max(
            len(flight_results),
            len(hotel_results),
            len(activity_results),
            len(member_preferences),
            1,
        )
        max_options = min(8, max_options)  # Allow up to 8 options (A-H)

        fallback_options: List[Dict[str, Any]] = []
        for idx in range(max_options):
            flight = flight_results[idx % len(flight_results)] if flight_results else {}
            hotel = hotel_results[idx % len(hotel_results)] if hotel_results else {}

            activities_subset: List[Dict[str, Any]] = []
            if activity_results:
                start_index = idx % len(activity_results)
                take = min(2, len(activity_results))
                for offset in range(take):
                    activities_subset.append(
                        activity_results[(start_index + offset) % len(activity_results)]
                    )

            destination = destination_for_option(flight, hotel, idx)
            flight_cost = self._safe_float(
                (flight.get("total_amount") if flight else None)
                or (flight.get("price") if flight else None)
                or (flight.get("price_per_person") if flight else None)
                or (flight.get("cost") if flight else None)
            )
            hotel_total = self._safe_float(
                (hotel.get("total_price") if hotel else None),
                0.0,
            )
            if hotel_total == 0.0:
                hotel_total = (
                    self._safe_float((hotel.get("price_per_night") if hotel else None))
                    * duration_days
                )
            activity_cost = sum(
                self._safe_float(
                    activity.get("price")
                    or activity.get("total_price")
                    or activity.get("cost")
                )
                for activity in activities_subset
            )
            estimated_total_cost = round(flight_cost + hotel_total + activity_cost, 2)
            cost_per_person = round(
                (
                    estimated_total_cost / group_size
                    if group_size
                    else estimated_total_cost
                ),
                2,
            )

            selected_activity_ids = [
                activity.get("id") or activity.get("external_id")
                for activity in activities_subset
                if activity.get("id") or activity.get("external_id")
            ]

            member_focus = (
                member_preferences[idx % len(member_preferences)].get("user")
                if member_preferences
                else "the group"
            )

            option_letter = letters[idx]
            fallback_options.append(
                {
                    "option_letter": option_letter,
                    "title": f"{destination} Fallback Option {option_letter}",
                    "description": (
                        "Deterministic fallback itinerary assembled from existing "
                        "flight, hotel, and activity data."
                    ),
                    "intended_destination": destination,
                    "selected_flight_id": (
                        flight.get("id") or flight.get("external_id")
                    ),
                    "selected_hotel_id": (hotel.get("id") or hotel.get("external_id")),
                    "selected_activity_ids": selected_activity_ids,
                    "estimated_total_cost": estimated_total_cost,
                    "cost_per_person": cost_per_person,
                    "ai_reasoning": (
                        "OpenAI response could not be parsed, so this option "
                        "uses the top available travel components as a stopgap."
                    ),
                    "compromise_explanation": (
                        f"Balances {member_focus}'s stated preferences with the "
                        "currently available search results."
                    ),
                    "pros": [
                        "Provides immediate option when AI output is invalid",
                        "Relies on real search data already fetched",
                    ],
                    "cons": [
                        "Lacks nuanced AI analysis; review manually",
                        "Activities may repeat if limited search results",
                    ],
                }
            )

        if not fallback_options:
            destination = (
                member_preferences[0].get("destination")
                if member_preferences
                else "Flexible Destination"
            )
            fallback_options.append(
                {
                    "option_letter": "A",
                    "title": f"{destination} Fallback Option",
                    "description": "AI output unavailable; please review search results manually.",
                    "intended_destination": destination,
                    "selected_flight_id": None,
                    "selected_hotel_id": None,
                    "selected_activity_ids": [],
                    "estimated_total_cost": 0.0,
                    "cost_per_person": 0.0,
                    "ai_reasoning": "Placeholder generated because AI JSON parsing failed.",
                    "compromise_explanation": "Collect additional data and retry AI generation.",
                    "pros": ["Highlights the failure quickly"],
                    "cons": ["No automated itinerary details"],
                }
            )

        summary_destination = fallback_options[0].get(
            "intended_destination", "the destination"
        )
        return {
            "options": fallback_options,
            "voting_guidance": (
                "Fallback options were generated automatically after a JSON parsing "
                "error from the AI response. Review cost estimates and customize "
                "before sharing with the group."
            ),
            "consensus_summary": (
                "AI parsing error prevented advanced analysis. Showing deterministic "
                f"options centered on {summary_destination} for quick review."
            ),
            "error": error_message,
            "fallback_used": True,
        }

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Convert common numeric representations to float without raising."""

        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            normalized = str(value).replace("$", "").replace(",", "").strip()
            return float(normalized) if normalized else default
        except (ValueError, TypeError):
            return default

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
