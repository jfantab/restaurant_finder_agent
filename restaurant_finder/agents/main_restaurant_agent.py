"""Main restaurant finder agent that coordinates the search process."""

from google.adk.agents import SequentialAgent
from .sub_agents.search_agent import create_search_agent
from .sub_agents.filter_agent import create_filter_agent
from .sub_agents.recommendation_agent import create_recommendation_agent
from .streamlined_restaurant_agent import create_streamlined_restaurant_agent


def create_main_restaurant_agent(use_cloud_mcp: bool = False, use_streamlined: bool = True):
    """Creates the main restaurant finder agent.

    Args:
        use_cloud_mcp: If True, uses FunctionTools directly.
                      If False, uses local stdio MCP server for SQL tools.
        use_streamlined: If True, uses optimized single-agent architecture (DEFAULT - 3-4x faster).
                        If False, uses legacy 3-agent sequential pipeline.

    Returns:
        Agent: Configured main restaurant finder agent
    """
    if use_streamlined:
        # NEW: Optimized single-agent architecture (3-4x faster)
        # Combines search + filter + recommendation into one agent
        # Eliminates 2 LLM round-trips, reducing latency from 8-12s to 2-3s
        return create_streamlined_restaurant_agent(use_cloud_mcp=use_cloud_mcp)
    else:
        # OLD: Legacy 3-agent sequential pipeline (kept for comparison)
        # SearchAgent -> FilterAgent -> RecommendationAgent
        # Each agent waits for previous completion = 8-12s total latency
        search_agent = create_search_agent(use_cloud_mcp=use_cloud_mcp)
        filter_agent = create_filter_agent(use_cloud_mcp=use_cloud_mcp)
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
