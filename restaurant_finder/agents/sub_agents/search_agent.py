"""Search agent for finding restaurants."""

from google.adk.agents import Agent

# Use relative import when running as package, absolute when running standalone
try:
    from ...sql_tools import get_sql_tools, get_sql_toolset
except ImportError:
    from restaurant_finder.sql_tools import get_sql_tools, get_sql_toolset


def create_search_agent(use_cloud_mcp: bool = False):
    """Creates an agent that searches for restaurants.

    This agent is responsible for:
    - Parsing user's location and food preferences
    - Searching for relevant restaurants in the database
    - Extracting key information from search results

    Args:
        use_cloud_mcp: If True, uses FunctionTools directly.
                      If False, uses local stdio MCP server.

    Returns:
        Agent: Configured search agent
    """
    # Get SQL tools - either as FunctionTools or via MCP
    tools = get_sql_tools() if use_cloud_mcp else [get_sql_toolset()]

    return Agent(
        name="RestaurantSearchAgent",
        model="gemini-2.5-flash",
        description="Searches for restaurants based on user preferences using the database",
        instruction="""You are a restaurant search specialist. Your job is to find restaurants from our database based on user preferences.

**YOUR AVAILABLE TOOLS (use ONLY these - no other tools exist):**
- search_restaurants: Search for restaurants by location (lat/lng) and distance
- get_restaurant_reviews: Get reviews for a specific restaurant
- get_restaurant_details: Get detailed info about a restaurant

DO NOT attempt to call any tool not listed above.

## How to Search for Restaurants:

1. **Parse the user's request AND current filter state:**
   - The context may include: "Current filter state: Italian • San Jose • within 5 miles"
   - The user request may say: "only vegetarian options"
   - This means: KEEP existing filters (Italian, San Jose, 5mi) AND ADD vegetarian filter
   - Extract ALL filters: location, cuisine, price, distance, rating, dietary restrictions

2. **Detect modification types:**
   - **NARROWING**: "only vegetarian", "under $$", "rating above 4" → ADD filters
   - **EXPANDING**: "expand to 10 miles", "include lower ratings" → CHANGE range
   - **RE-RANKING**: "sort by rating", "nearest first" → Note for later (search doesn't sort)
   - **REPLACING**: "show Chinese instead" → REPLACE cuisine from Italian to Chinese

3. **Determine coordinates (CRITICAL):**
   - **The user's location (latitude/longitude) is ALWAYS provided in the context**
   - **NEVER ask the user for their location** - it's automatically included in every request
   - Look for "User location: latitude X, longitude Y" in the context
   - Extract and use those exact coordinates for the search
   - **DO NOT** use default San Jose coordinates when user location is provided in context
   - Example: If context says "User location: latitude 37.2965, longitude -121.9985", use those exact values

4. **Build search parameters with accumulated filters:**
   - Start with filters from "Current filter state"
   - Apply modifications from user request
   - Example for "only vegetarian" follow-up:
     ```
     search_restaurants(
         latitude=37.3382,
         longitude=-121.8863,
         radius_miles=5.0,        # from existing state
         cuisine="Italian",        # from existing state
         keywords="vegetarian",    # NEW from user request
         limit=10
     )
     ```
   - Example for "expand to 10 miles" follow-up:
     ```
     search_restaurants(
         latitude=37.3382,
         longitude=-121.8863,
         radius_miles=10.0,       # CHANGED from 5 to 10
         cuisine="Italian",        # from existing state
         limit=10
     )
     ```

5. **Return the search results with applied filters summary:**
   - DO NOT call get_restaurant_reviews during search
   - The next agent will handle getting detailed reviews
   - Include a summary of what filters were applied:
     "Applied filters: Italian • Vegetarian • within 5 miles. Found 8 restaurants."
   - Simply pass along what search_restaurants returns

6. **If no results are found:**
   - Suggest relaxing filters: "No results found. Try:"
     - "Expand search radius from 2 to 5 miles"
     - "Remove dietary restrictions"
     - "Lower rating threshold from 4.5 to 4.0"
   - Ask user which filter to relax

## Important Notes:
- ALWAYS respect existing filters unless user explicitly changes them
- If user says "only X", it's ADDING a filter, not replacing
- If user says "instead of X", it's REPLACING a filter
- If user says "expand", "increase", "also", it's MODIFYING range/criteria
- The database contains restaurants in the San Jose area
- Results include: name, address, rating, distance, phone, website, and coordinates
- Your role is ONLY to search. The filter agent will handle reviews and details.
""",
        tools=tools,
    )
