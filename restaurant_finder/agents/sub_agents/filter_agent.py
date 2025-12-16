"""Filter agent for refining restaurant recommendations."""

import logging
from google.adk.agents import Agent

# Set up logging for debugging coordinate extraction
logger = logging.getLogger(__name__)

# Use relative import when running as package, absolute when running standalone
try:
    from ...google_tools import get_google_places_toolset, get_google_places_function_tools
except ImportError:
    from google_tools import get_google_places_toolset, get_google_places_function_tools


def after_tool_callback(**kwargs):
    """Callback to log tool responses for debugging coordinate extraction."""
    tool = kwargs.get("tool")
    tool_response = kwargs.get("tool_response")

    tool_name = getattr(tool, "name", str(tool)) if tool else "unknown"

    if "get_place_details" in str(tool_name).lower():
        # Log the response to verify coordinates are being fetched
        if isinstance(tool_response, dict):
            lat = tool_response.get("latitude") or tool_response.get("lat")
            lng = tool_response.get("longitude") or tool_response.get("lng")
            name = tool_response.get("name", "Unknown")
            logger.info(f"[FilterAgent] get_place_details for '{name}': lat={lat}, lng={lng}")
            if not lat or not lng:
                logger.warning(f"[FilterAgent] Missing coordinates for '{name}' - response keys: {list(tool_response.keys())}")
        else:
            logger.warning(f"[FilterAgent] get_place_details returned non-dict: {type(tool_response)}")

    return tool_response


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

**YOUR AVAILABLE TOOLS (use ONLY these - no other tools exist):**
- get_place_details: Get detailed info about a restaurant using its Place ID
- search_places: Search for additional restaurants if needed
- search_nearby: Find restaurants near coordinates

DO NOT attempt to call any tool not listed above (e.g., there is NO "recommend_restaurants" tool).

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

When passing data to the recommendation agent, format each restaurant with ALL available fields:
- name, address, phone, website
- latitude, longitude (CRITICAL - extract from geometry.location in place details)
- rating (convert to 0-10 scale if needed)
- price_level (convert to $, $$, $$$, $$$$)
- opening_hours (is currently open?)
""",
        tools=get_google_places_function_tools() if use_cloud_mcp else [get_google_places_toolset()],
        after_tool_callback=after_tool_callback,
    )
