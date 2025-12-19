"""AgentTool wrapper for the restaurant finder agent."""

from google.adk.tools.agent_tool import AgentTool
from ..agents.main_restaurant_agent import create_main_restaurant_agent


def create_restaurant_agent_tool(
    use_cloud_mcp: bool = False, skip_summarization: bool = False
) -> AgentTool:
    """Create an AgentTool wrapper around the restaurant finder agent.

    This allows the restaurant finder agent to be used as a tool by other agents,
    such as the router agent.

    Args:
        use_cloud_mcp: If True, uses Cloud Run deployed MCP server.
                       If False, uses local stdio MCP server.
        skip_summarization: If False (default), allows the parent agent's
            after_tool_callback to intercept and return the result directly.

    Returns:
        AgentTool wrapping the restaurant finder agent.
    """
    agent = create_main_restaurant_agent(use_cloud_mcp=use_cloud_mcp)
    return AgentTool(agent=agent, skip_summarization=skip_summarization)
