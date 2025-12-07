#!/usr/bin/env python3
"""
Deploy restaurant finder agent to Vertex AI Agent Engine with Cloud MCP support.

This script deploys the restaurant finder agent that uses the Apple Maps MCP server
running on Cloud Run via SSE connection.
"""

import os
import vertexai
from vertexai import agent_engines
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
AGENT_NAME = "restaurant_finder_agent"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-staging"  # Or use existing bucket

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

print(f"Deploying {AGENT_NAME} to Vertex AI Agent Engine...")
print(f"Project: {PROJECT_ID}")
print(f"Location: {LOCATION}")

# Clean up existing deployment
print(f"\n🧹 Cleaning up existing {AGENT_NAME} deployment...")
try:
    agents_list = list(agent_engines.list())
    existing_agent = next((agent for agent in agents_list if agent.display_name == AGENT_NAME), None)

    if existing_agent:
        print(f"Found existing agent: {existing_agent.resource_name}")
        agent_engines.delete(resource_name=existing_agent.resource_name, force=True)
        print(f"✅ Deleted existing agent")
    else:
        print(f"No existing agent found with name '{AGENT_NAME}'")
except Exception as e:
    print(f"⚠️ Cleanup warning: {e}")
    print("Continuing with deployment...")

print()

# Set environment to force Cloud MCP mode before importing
os.environ["USE_CLOUD_MCP"] = "true"

# Import the agent creation function (not the agent instance)
from agents import create_main_restaurant_agent

# Create agent with Cloud MCP enabled
root_agent = create_main_restaurant_agent(use_cloud_mcp=True)

# Deploy agent with Apple Maps MCP support via Cloud Run
remote_agent = agent_engines.create(
    root_agent,  # Pass agent as positional argument
    display_name=AGENT_NAME,
    description="Restaurant finder with Apple Maps MCP integration via Cloud Run",
    requirements=[
        "google-adk",
        "opentelemetry-instrumentation-google-genai",
        "mcp",
        "python-dotenv",
        "google-cloud-aiplatform",
        "requests",
    ],
    extra_packages=[
        "agents",  # Include agent modules
        "apple_tools",   # Include Apple Maps tool modules
        "google_tools",  # Include Google Places tool modules
    ],
    env_vars={
        "APPLE_MAPS_MCP_URL": os.getenv("APPLE_MAPS_MCP_URL", ""),
        "GOOGLE_PLACES_MCP_URL": os.getenv("GOOGLE_PLACES_MCP_URL", ""),
        "USE_CLOUD_MCP": "true",  # Always use Cloud MCP in Vertex AI
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
        # Note: GOOGLE_CLOUD_LOCATION and GOOGLE_CLOUD_PROJECT are reserved and automatically set
    },
)

print(f"\n✅ Agent deployed successfully!")
print(f"Resource name: {remote_agent.resource_name}")
print(f"\nThe agent is now deployed with Apple Maps MCP via Cloud Run!")
print(f"MCP Server: {os.getenv('APPLE_MAPS_MCP_URL')}")
