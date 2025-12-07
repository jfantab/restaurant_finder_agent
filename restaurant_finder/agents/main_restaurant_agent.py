"""Main restaurant finder agent that coordinates the search process."""

from google.adk.agents import SequentialAgent
from .sub_agents.search_agent import create_search_agent
from .sub_agents.filter_agent import create_filter_agent
from .sub_agents.recommendation_agent import create_recommendation_agent


def create_main_restaurant_agent(use_cloud_mcp: bool = False):
    """Creates the main restaurant finder agent.

    The agent uses a sequential workflow:
    1. SearchAgent: Searches for restaurants using Google Maps based on user preferences
    2. FilterAgent: Filters and ranks results based on detailed information from Google Places
    3. RecommendationAgent: Presents final recommendations to the user

    Args:
        use_cloud_mcp: If True, uses Cloud Run deployed MCP server.
                      If False, uses local stdio MCP server.

    Returns:
        SequentialAgent: Configured main restaurant finder agent
    """
    # Stage 1: Search for restaurants
    search_agent = create_search_agent(use_cloud_mcp=use_cloud_mcp)

    # Stage 2: Filter and rank results
    filter_agent = create_filter_agent(use_cloud_mcp=use_cloud_mcp)

    # Stage 3: Present recommendations
    recommendation_agent = create_recommendation_agent()

    return SequentialAgent(
        name="restaurant_finder",
        description="AI agent that finds and recommends restaurants based on user preferences",
        sub_agents=[
            search_agent,
            filter_agent,
            recommendation_agent,
        ],
    )
