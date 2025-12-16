"""Recommendation agent for presenting final restaurant suggestions."""

from google.adk.agents import Agent
from pydantic import BaseModel, Field
from typing import List, Optional


class Review(BaseModel):
    """Schema for a single review."""
    author: str = Field(..., description="Name of the reviewer")
    rating: Optional[float] = Field(None, description="Rating given by reviewer (1-5 stars)")
    text: str = Field(..., description="Review text content")


class RestaurantRecommendation(BaseModel):
    """Schema for a single restaurant recommendation."""
    name: str = Field(..., description="Name of the restaurant")
    cuisine_type: str = Field(..., description="Type of cuisine (e.g., Italian, Japanese)")
    rating: Optional[float] = Field(None, description="Restaurant rating (0-10 scale)")
    price_level: Optional[str] = Field(None, description="Price level ($, $$, $$$, $$$$)")
    address: str = Field(..., description="Full street address")
    distance_miles: Optional[float] = Field(None, description="Distance from user in miles")
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    is_open: Optional[bool] = Field(None, description="Whether the restaurant is currently open")
    description: str = Field(..., description="Brief description of why this restaurant is recommended")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    standout_features: Optional[List[str]] = Field(None, description="Notable features or specialties")
    reviews: Optional[List[Review]] = Field(None, description="Recent reviews from Google Places")


class RestaurantRecommendations(BaseModel):
    """Schema for the complete list of restaurant recommendations."""
    summary: str = Field(..., description="Brief summary of why these restaurants were chosen")
    restaurants: List[RestaurantRecommendation] = Field(..., description="List of recommended restaurants")
    additional_notes: Optional[str] = Field(None, description="Additional helpful information or suggestions")


def create_recommendation_agent():
    """Creates an agent that presents final restaurant recommendations.

    This agent is responsible for:
    - Formatting filtered results into clear recommendations
    - Providing helpful context for each restaurant
    - Adding practical details (directions, contact info)
    - Answering follow-up questions

    Returns:
        Agent: Configured recommendation agent
    """
    return Agent(
        name="RestaurantRecommendationAgent",
        model="gemini-2.5-flash",
        description="Presents final restaurant recommendations as structured data",
        instruction="""You are a restaurant recommendation specialist. Your job is to:

**YOU HAVE NO TOOLS. DO NOT ATTEMPT TO CALL ANY TOOLS.**
Your only job is to format the restaurant data from the filter agent into a JSON response.

1. Review the filtered and ranked restaurants from previous agents

2. Extract and structure the following information for each restaurant:
   - Name and cuisine type
   - Address with coordinates (latitude, longitude) - CRITICAL: Include actual coordinate values from the filter agent
   - Rating (on 0-10 scale) and price level ($, $$, $$$, $$$$)
   - Distance from user's location in miles
   - Contact info (phone, website)
   - Current open/closed status
   - Description of why it's a good match for the user
   - Standout features or specialties
   - Reviews from Google Places (author, rating, text) - include up to 3 recent reviews if available

3. Create a summary explaining:
   - Why these restaurants were chosen
   - Any trade-offs or notable aspects
   - Overall recommendation context

4. Add helpful additional notes if relevant:
   - Best time to visit
   - Reservation recommendations
   - Alternative suggestions

CRITICAL REQUIREMENTS:
1. You MUST include the latitude and longitude coordinates for each restaurant.
   These coordinates are provided by the filter agent and are essential for displaying
   restaurants on the map. DO NOT set coordinates to null - extract them from the
   filter agent's detailed information.

2. You MUST use only straight ASCII double quotes (") in your JSON output.
   Do NOT use curly/smart quotes (" " ' '). This will break JSON parsing.

3. Return ONLY the raw JSON object - no markdown code blocks, no backticks, no extra text.

You MUST return your response as a valid JSON object following this exact schema:

{
  "summary": "Brief summary of why these restaurants were chosen",
  "restaurants": [
    {
      "name": "Restaurant name",
      "cuisine_type": "Type of cuisine",
      "rating": 8.5,
      "price_level": "$$",
      "address": "Full street address",
      "distance_miles": 0.5,
      "phone": "(555) 123-4567",
      "website": "https://example.com",
      "is_open": true,
      "description": "Why this restaurant is recommended",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "standout_features": ["Feature 1", "Feature 2"],
      "reviews": [
        {"author": "John D.", "rating": 5, "text": "Amazing food and great service!"},
        {"author": "Jane S.", "rating": 4, "text": "Delicious pasta, will come back."}
      ]
    }
  ],
  "additional_notes": "Optional additional helpful information"
}

Include 3-5 top restaurant recommendations ranked by relevance to the user's preferences.

FINAL REMINDER: Output ONLY valid JSON with straight ASCII quotes. No markdown, no code blocks, no explanatory text.
""",
        tools=[],
        output_schema=RestaurantRecommendations,
    )
