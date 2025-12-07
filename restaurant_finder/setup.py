"""Setup and initialization for restaurant finder agent."""

import os
import vertexai


def setup_environment():
    """Initialize environment variables and Vertex AI

    Note: When deployed to Agent Engine, environment variables should already be set.
    For local testing, use .env file with python-dotenv.
    """
    # Increase timeout for authentication and API calls
    os.environ.setdefault('GOOGLE_AUTH_TOKEN_URI_TIMEOUT', '300')  # 5 minutes
    os.environ.setdefault('GOOGLE_API_TIMEOUT', '300')  # 5 minutes

    # Try to load dotenv for local development (optional)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # dotenv not available - that's fine for deployed environments
        pass

    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
    USE_CLOUD_MCP = os.getenv("USE_CLOUD_MCP", "").lower() == "true"
    GOOGLE_PLACES_MCP_URL = os.getenv("GOOGLE_PLACES_MCP_URL")

    if not PROJECT_ID:
        raise ValueError("⚠️ GOOGLE_CLOUD_PROJECT not found in environment variables")
    if not LOCATION:
        raise ValueError("⚠️ GOOGLE_CLOUD_LOCATION not found in environment variables")

    # Check credentials based on MCP mode
    if USE_CLOUD_MCP:
        if not GOOGLE_PLACES_MCP_URL:
            raise ValueError(
                "⚠️ USE_CLOUD_MCP is true but GOOGLE_PLACES_MCP_URL not set.\n"
                "Set GOOGLE_PLACES_MCP_URL to your Cloud Run service URL"
            )
        print(f"✅ Using Cloud Run MCP server: {GOOGLE_PLACES_MCP_URL}")
    else:
        GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

        if not GOOGLE_PLACES_API_KEY:
            raise ValueError(
                "⚠️ Google Places API key not found in environment variables.\n"
                "Required: GOOGLE_PLACES_API_KEY\n"
                "Get it at https://console.cloud.google.com/apis/credentials"
            )
        print(f"✅ Google Places API key configured (local MCP)")

    if PROJECT_ID == "your-project-id":
        raise ValueError("⚠️ Please replace 'your-project-id' with your actual Google Cloud Project ID.")

    print(f"✅ Project ID set to: {PROJECT_ID}")

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
    )
