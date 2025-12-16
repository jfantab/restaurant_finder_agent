"""Router agent that coordinates restaurant finder requests."""

from google.adk.agents import Agent
from agent_tools.restaurant_agent_tool import create_restaurant_agent_tool


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
                return {"result": result}

    return tool_response


ROUTER_INSTRUCTION = """You are a helpful Restaurant Finder Coordinator.

**Your Task:**
Assess the user's request and either route to the restaurant search tool or handle directly.

**Available Tools:**
- restaurant_finder_agent: USE ONLY when user wants to search for/discover new restaurants

**CRITICAL: When to use restaurant_finder_agent (ONLY these cases):**
- "Find restaurants near X"
- "Search for [cuisine] food in [location]"
- "Where can I get [food type] in [location]?"
- "Recommend restaurants for [occasion] in [location]"
- "What are good restaurants in [area]?"
- "I'm looking for a place to eat near..."
- Any NEW restaurant search/discovery request

**CRITICAL: When to respond DIRECTLY (do NOT use tools):**
- "Tell me more about [restaurant from previous results]"
- "What are the hours?" -> Answer from context
- "Is it expensive?" -> Answer from context
- "Which one has the best rating?" -> Answer from context
- "What's the address of [restaurant]?" -> Answer from context
- Any follow-up question about previous results
- General food/dining questions
- Clarification requests
- "Thanks" or acknowledgments

**Decision Logic:**
- Default to responding DIRECTLY for follow-ups and clarifications
- Only use restaurant_finder_agent for NEW search requests
- Be helpful and conversational in direct responses

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
