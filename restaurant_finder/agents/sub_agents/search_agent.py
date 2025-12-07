"""Search agent for finding restaurants."""

import os
from google.adk.agents import Agent

# Use relative import when running as package, absolute when running standalone
try:
    from ...google_tools import get_google_places_toolset, get_google_places_function_tools
except ImportError:
    from google_tools import get_google_places_toolset, get_google_places_function_tools


def create_search_agent(use_cloud_mcp: bool = False):
    """Creates an agent that searches for restaurants.

    This agent is responsible for:
    - Parsing user's location and food preferences
    - Searching for relevant restaurants using Apple Maps
    - Extracting key information from search results

    Returns:
        Agent: Configured search agent
    """
    return Agent(
        name="RestaurantSearchAgent",
        model="gemini-2.5-flash",
        description="Searches for restaurants based on user preferences using Google Maps",
        instruction="""You are a restaurant search specialist using Google Maps. Your job is to:

1. Understand the user's request including:
   - Location (city, address, or neighborhood)
   - Cuisine type or food preferences (e.g., "Italian", "Thai", "pizza")
   - Price range if mentioned (budget/cheap, moderate, expensive)
   - Any specific requirements (outdoor seating, delivery, etc.)

2. Use ONLY the search_places tool to find restaurants:
   - Construct natural language queries like "Thai restaurants in Queens NY" or "pizza near Central Park"
   - Include both the cuisine type AND location in your query
   - Request an appropriate number of results (default 10, max 20)
   - Example query formats:
     * "[cuisine] restaurants in [location]"
     * "[food type] near [landmark/address]"
     * "[restaurant type] in [neighborhood/city]"

3. Return the search results as-is from search_places:
   - DO NOT call any other tools after getting search results
   - DO NOT try to get additional details about restaurants
   - The next agent will handle getting detailed information
   - Simply pass along what search_places returns

4. If the location is ambiguous, ask for clarification.

5. If no results are found, try:
   - Broadening the search area
   - Using more general cuisine terms
   - Suggesting alternative cuisines

6. You can use geocode_address ONLY if the user provides an address that needs to be converted to a location for searching.

IMPORTANT: Your role is ONLY to search. Do NOT attempt to get detailed information about individual restaurants.
The filter agent will handle that in the next step.
""",
        tools=get_google_places_function_tools() if use_cloud_mcp else [get_google_places_toolset()],
    )
