"""Main entry point for restaurant finder agent."""

import os
from setup import setup_environment
from agents import create_main_restaurant_agent

# Initialize environment and Vertex AI
setup_environment()

# Check if we should use Cloud Run MCP server (default: True for cloud SSE)
use_cloud_mcp = os.getenv("USE_CLOUD_MCP", "true").lower() == "true"

# Restaurant Finder Agent: Sequential flow through search, filter, and recommendation
root_agent = create_main_restaurant_agent(use_cloud_mcp=use_cloud_mcp)
