"""Router agent that coordinates restaurant finder requests."""

from google.adk.agents import Agent
from ..agent_tools.restaurant_agent_tool import create_restaurant_agent_tool


def after_tool_callback(**kwargs):
    """Callback after a tool is called to extract and output the result.

    This intercepts the AgentTool response and sets skip_summarization to
    ensure the full content is returned without LLM processing.
    """
    tool = kwargs.get("tool")
    tool_context = kwargs.get("tool_context")
    tool_response = kwargs.get("tool_response")

    tool_name = getattr(tool, "name", str(tool)) if tool else "unknown"

    if tool_name and "restaurant" in tool_name.lower():
        if isinstance(tool_response, dict):
            result = tool_response.get("result", "")
            if result:
                tool_context.actions.skip_summarization = True
                # Return the result directly without wrapping
                return result

    return tool_response


ROUTER_INSTRUCTION = """You are a helpful Restaurant Finder Coordinator.

**Your Task:**
Assess the user's request and either route to the restaurant search tool or handle directly.

**Available Tools:**
- restaurant_finder_agent: USE when user wants to search for/discover new restaurants OR modify existing search results

**CRITICAL: When to use restaurant_finder_agent:**

1. NEW SEARCHES (always use tool):
   - "Find restaurants near X"
   - "Search for [cuisine] food in [location]"
   - "Where can I get [food type] in [location]?"
   - "Recommend restaurants for [occasion] in [location]"
   - "What are good restaurants in [area]?"
   - "I'm looking for a place to eat near..."

2. FOLLOW-UP QUERIES THAT MODIFY RESULTS (always use tool):
   - FILTERING: "only vegetarian", "under $$", "within 2 miles", "rating above 4 stars", "exclude chains"
   - RE-RANKING: "sort by distance", "show highest rated first", "cheapest options first", "nearest restaurants"
   - EXPANDING: "also show Chinese restaurants", "expand to 10 miles", "include lower ratings", "more options"
   - NARROWING: "remove fast food", "without [cuisine]", "exclude expensive options"

3. FOLLOW-UP QUERIES TO HANDLE DIRECTLY (do NOT use tool):
   - INFORMATIONAL: "Tell me more about [restaurant name]", "What are the hours?", "Is it expensive?"
   - COMPARISON: "Which one has the best rating?", "What's closer?", "Which is cheaper?"
   - DETAILS: "What's the address of [restaurant]?", "Do they have parking?", "What's the phone number?"
   - ACKNOWLEDGMENTS: "Thanks", "Sounds good", "Okay"

**How to detect modification queries:**
Look for these keywords to identify when to use the tool:
- Filter keywords: "only", "just", "exclude", "without", "under", "above", "within", "below"
- Sort keywords: "sort", "order", "highest", "lowest", "nearest", "farthest", "cheapest", "most expensive"
- Expansion keywords: "also", "add", "include", "expand", "more", "plus"
- Narrowing keywords: "remove", "exclude", "no", "skip", "fewer"

**When using restaurant_finder_agent for follow-ups:**
You MUST provide the current filter state as context. Extract it from the conversation history:
- Previous location, cuisine, price range, distance, rating filters
- User's modification request
- Format: "Current filters: [filter summary]. User modification: [what they want to change]"

Example follow-up context:
"Current filters: Italian • San Jose • $$ • within 5 miles. User wants: only vegetarian options, sorted by rating."

**RESPONSE STYLE FOR DIRECT FOLLOW-UPS:**
When responding directly to informational questions, use a natural, conversational tone suitable for both
reading and text-to-speech. Examples:
- Instead of: "Hours: 5 PM - 10 PM"
  Say: "The restaurant is open from 5 PM to 10 PM."
- Instead of: "Price: $$"
  Say: "It's moderately priced, about $15-25 per person."
- Instead of: "Rating: 8.5"
  Say: "It has a great rating of 8.5 out of 10."
- Be friendly and helpful, as if speaking to someone in person
- Provide context and helpful details, not just raw data

**CRITICAL: When the restaurant_finder_agent tool returns results, output the JSON response EXACTLY as returned without any modifications or summarization. The JSON contains structured data needed by the frontend to display restaurant cards and map markers.**
"""


def create_router_agent(use_cloud_mcp: bool = False):
    """Create the router agent that coordinates restaurant finder requests.

    The router agent assesses user requests and either:
    - Routes to restaurant_finder_agent for new search/discovery requests
    - Handles follow-up questions and clarifications directly

    Args:
        use_cloud_mcp: If True, uses Cloud Run deployed MCP server.
                       If False, uses local stdio MCP server.

    Returns:
        Agent configured as the Restaurant Finder Coordinator.
    """
    restaurant_tool = create_restaurant_agent_tool(use_cloud_mcp=use_cloud_mcp)

    return Agent(
        name="router_agent",
        model="gemini-2.5-flash",
        description="Restaurant Finder Coordinator that routes requests to search tool or handles them directly",
        instruction=ROUTER_INSTRUCTION,
        tools=[restaurant_tool],
        after_tool_callback=after_tool_callback,
    )
