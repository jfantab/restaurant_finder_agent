# Google Places MCP Server

This directory contains a Model Context Protocol (MCP) server that exposes Google Places API functionality for AI agents.

## Features

- **Text Search**: Search for places using natural language queries
- **Place Details**: Get comprehensive information about specific places
- **Nearby Search**: Find places near coordinates with type and keyword filters
- **Autocomplete**: Get autocomplete suggestions for place searches
- **Geocoding**: Convert addresses to geographic coordinates

## Files

- `google_places_mcp.py` - Core MCP server implementation with all tools
- `app.py` - Starlette wrapper exposing both SSE (MCP) and REST endpoints
- `google_places_toolset.py` - Local MCP toolset wrapper for Google ADK agents
- `google_places_toolset_cloud.py` - Cloud Run MCP toolset wrapper
- `google_places_function_tool.py` - Pickle-safe FunctionTools for Vertex AI deployment
- `Dockerfile` - Container configuration for Cloud Run
- `deploy.sh` - Automated deployment script
- `requirements.txt` - Python dependencies

## Setup

### 1. Get Google Places API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Places API (New)
4. Create credentials (API Key)
5. Copy your API key

### 2. Configure Environment

Add to your `.env` file:

```bash
GOOGLE_PLACES_API_KEY=your_api_key_here
```

### 3. Local Development

Run the MCP server locally:

```bash
cd google_tools
python google_places_mcp.py
```

Or use the toolset in your agent:

```python
from google_tools import get_google_places_toolset

toolset = get_google_places_toolset()
```

## Cloud Run Deployment

### Prerequisites

1. Google Cloud Project with billing enabled
2. gcloud CLI installed and configured
3. Google Places API key stored in Secret Manager

### Store API Key in Secret Manager

```bash
# Store the secret
echo -n "your_api_key_here" | gcloud secrets create GOOGLE_PLACES_API_KEY --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding GOOGLE_PLACES_API_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Deploy to Cloud Run

```bash
cd google_tools
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Set the GCP project
2. Enable required APIs
3. Deploy to Cloud Run with secrets
4. Display the service URL

### Use Cloud Deployment

After deployment, set the environment variable:

```bash
export GOOGLE_PLACES_MCP_URL="https://google-places-mcp-xxxxx-uw.a.run.app/sse"
```

Then use in your agent:

```python
from google_tools import get_google_places_cloud_toolset

toolset = get_google_places_cloud_toolset()
# Or pass URL directly:
# toolset = get_google_places_cloud_toolset("https://your-service-url/sse")
```

## Available Tools

### search_places

Search for places using natural language queries.

```python
result = search_places(
    query="Thai restaurants",
    location="New York, NY",  # Optional
    radius_meters=5000,       # Default: 5000
    limit=5                   # Default: 5, max: 20
)
```

### get_place_details

Get detailed information about a specific place.

```python
result = get_place_details(place_id="ChIJN1t_tDeuEmsRUsoyG83frY4")
```

Returns: ratings, reviews, hours, contact info, photos, and more.

### search_nearby

Find places near coordinates.

```python
result = search_nearby(
    latitude=37.7749,
    longitude=-122.4194,
    place_type="restaurant",  # Optional
    keyword="thai",           # Optional
    radius_meters=1000,       # Default: 1000
    limit=10                  # Default: 10, max: 20
)
```

### autocomplete_places

Get autocomplete suggestions.

```python
result = autocomplete_places(
    input_text="Golden Gate",
    location="San Francisco, CA"  # Optional
)
```

### geocode_address

Convert address to coordinates.

```python
result = geocode_address(address="1600 Amphitheatre Parkway, Mountain View, CA")
```

## Vertex AI Deployment

For Vertex AI Agent Engine deployment, use FunctionTools instead of McpToolset:

```python
from google_tools import get_google_places_function_tools

tools = get_google_places_function_tools()
# These tools are pickleable and work with Vertex AI
```

**Requirements:**
- Set `GOOGLE_PLACES_MCP_URL` environment variable pointing to your Cloud Run service
- The Cloud Run service must be deployed and accessible

## Endpoints

When deployed to Cloud Run, the server exposes:

- **SSE Endpoint**: `https://your-service/sse` - MCP protocol for local agents
- **REST API**: `https://your-service/api/*` - HTTP endpoints for FunctionTools
  - POST `/api/search_places`
  - POST `/api/get_place_details`
  - POST `/api/search_nearby`
  - POST `/api/autocomplete_places`
  - POST `/api/geocode_address`
- **Health Check**: GET `/health` - Cloud Run health monitoring

## Documentation

- [Google Places API (New) Overview](https://developers.google.com/maps/documentation/places/web-service/overview)
- [Places API Setup](https://developers.google.com/maps/documentation/places/web-service/get-api-key)
- [Model Context Protocol](https://modelcontextprotocol.io/)
