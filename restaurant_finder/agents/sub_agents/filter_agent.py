"""Filter agent for refining restaurant recommendations."""

import logging
from google.adk.agents import Agent

# Set up logging for debugging coordinate extraction
logger = logging.getLogger(__name__)

# Use relative import when running as package, absolute when running standalone
try:
    from ...sql_tools import get_sql_toolset, get_sql_tools
except ImportError:
    from sql_tools import get_sql_toolset, get_sql_tools


def after_tool_callback(**kwargs):
    """Callback to log tool responses for debugging coordinate extraction."""
    tool = kwargs.get("tool")
    tool_response = kwargs.get("tool_response")

    tool_name = getattr(tool, "name", str(tool)) if tool else "unknown"

    if "get_restaurant_details" in str(tool_name).lower():
        # Log the response to verify coordinates are being fetched
        if isinstance(tool_response, dict):
            lat = tool_response.get("latitude") or tool_response.get("lat")
            lng = tool_response.get("longitude") or tool_response.get("lng")
            name = tool_response.get("name", "Unknown")
            logger.info(f"[FilterAgent] get_restaurant_details for '{name}': lat={lat}, lng={lng}")
            if not lat or not lng:
                logger.warning(f"[FilterAgent] Missing coordinates for '{name}' - response keys: {list(tool_response.keys())}")
        else:
            logger.warning(f"[FilterAgent] get_restaurant_details returned non-dict: {type(tool_response)}")

    return tool_response


def create_filter_agent(use_cloud_mcp: bool = False):
    """Creates an agent that filters and refines restaurant search results.

    This agent is responsible for:
    - Analyzing search results from the search agent
    - Getting detailed information for promising restaurants
    - Filtering based on user preferences and requirements
    - Ranking restaurants by relevance

    Args:
        use_cloud_mcp: If True, uses FunctionTools directly.
                      If False, uses local stdio MCP server.

    Returns:
        Agent: Configured filter agent
    """
    return Agent(
        name="RestaurantFilterAgent",
        model="gemini-2.5-flash",
        description="Filters and refines restaurant search results based on detailed information",
        instruction="""You are a restaurant filtering specialist. Your job is to:

**YOUR AVAILABLE TOOLS (use ONLY these - no other tools exist):**
- get_restaurants_with_reviews_batch: Get details + reviews for MULTIPLE restaurants in ONE call (PREFERRED - 10x faster!)
- get_restaurant_details: Get detailed info about ONE restaurant (fallback only)
- get_restaurant_reviews: Get reviews for ONE restaurant (fallback only)
- search_restaurants: Search for additional restaurants if needed

DO NOT attempt to call any tool not listed above (e.g., there is NO "recommend_restaurants" tool).

1. Analyze the search results from the previous agent:
   - Review all restaurants found
   - Identify the most promising candidates (top 5-8 restaurants)
   - Extract their place_ids into a list

2. Get ALL data in ONE BATCH CALL (this is 10x faster than individual calls):
   - CRITICAL: Use get_restaurants_with_reviews_batch with the list of place_ids AND user coordinates
   - Extract user_latitude and user_longitude from the context (format: "User location: latitude X, longitude Y")
   - Pass these coordinates to get accurate distance calculations
   - This returns details + reviews + distances for ALL restaurants at once
   - ONLY use get_restaurant_details or get_restaurant_reviews individually if the batch call fails
   - Example: get_restaurants_with_reviews_batch(place_ids=["id1", "id2", "id3"], reviews_limit=10, user_latitude=37.2965, user_longitude=-121.9985)

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

IMPORTANT: The batch tool returns ALL required data including:
- name, address, phone, website
- latitude, longitude (CRITICAL for map display)
- distance_miles (when user coordinates are provided)
- rating, review_count
- categories, hours
- reviews array (up to 10 reviews with author, rating, text, date)

**USER CONTEXT:**
- The user's location coordinates are ALWAYS provided in the context
- Format: "User location: latitude X, longitude Y"
- ALWAYS extract and pass these to get_restaurants_with_reviews_batch for accurate distances

DO NOT make individual tool calls unless absolutely necessary. The batch tool is 10x faster!
""",
        tools=get_sql_tools() if use_cloud_mcp else [get_sql_toolset()],
        after_tool_callback=after_tool_callback,
    )
