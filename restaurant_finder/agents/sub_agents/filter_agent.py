"""Filter agent for refining restaurant recommendations."""

from google.adk.agents import Agent

# Use relative import when running as package, absolute when running standalone
try:
    from ...google_tools import get_google_places_toolset, get_google_places_function_tools
except ImportError:
    from google_tools import get_google_places_toolset, get_google_places_function_tools


def create_filter_agent(use_cloud_mcp: bool = False):
    """Creates an agent that filters and refines restaurant search results.

    This agent is responsible for:
    - Analyzing search results from the search agent
    - Getting detailed information for promising restaurants
    - Filtering based on user preferences and requirements
    - Ranking restaurants by relevance

    Returns:
        Agent: Configured filter agent
    """
    return Agent(
        name="RestaurantFilterAgent",
        model="gemini-2.5-flash",
        description="Filters and refines restaurant search results based on detailed information",
        instruction="""You are a restaurant filtering specialist. Your job is to:

1. Analyze the search results from the previous agent:
   - Review all restaurants found
   - Identify the most promising candidates (top 5-8 restaurants)

2. Get detailed information INCLUDING COORDINATES for ALL top candidates:
   - CRITICAL: Use get_place_details tool for EACH restaurant to get latitude/longitude coordinates
   - This is REQUIRED - coordinates are needed to display restaurants on the map
   - Also get phone numbers, websites, and other details
   - Verify location details

3. Filter restaurants based on:
   - User's stated preferences (cuisine, price, location)
   - Practical factors (distance)
   - Any specific requirements mentioned

4. Rank the filtered results:
   - Prioritize best matches for user's needs
   - Consider distance and relevance
   - Keep top 5-8 restaurants for recommendation

5. Prepare structured data for the recommendation agent:
   - Organize by relevance
   - Include ALL details especially coordinates (latitude, longitude) for EACH restaurant
   - Note why each restaurant is a good match
   - Pass complete information so recommendation agent can format properly

IMPORTANT: You MUST call get_place_details for each restaurant you're recommending to ensure
the recommendation agent has coordinates to display restaurants on the map. Without coordinates,
restaurants cannot be shown on the map!
""",
        tools=get_google_places_function_tools() if use_cloud_mcp else [get_google_places_toolset()],
    )
