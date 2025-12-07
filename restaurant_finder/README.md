# Restaurant Finder Agent

A Google Vertex AI agent that recommends restaurants using the Mapbox Search API. The agent uses a sequential workflow to search, filter, and present restaurant recommendations based on user preferences.

## Architecture

The agent consists of three sequential sub-agents:

1. **SearchAgent**: Searches for restaurants using Mapbox Search API
   - Parses user location and food preferences
   - Calls Mapbox API with appropriate filters
   - Returns comprehensive search results

2. **FilterAgent**: Filters and ranks search results
   - Gets detailed information for promising restaurants
   - Filters based on user preferences and quality indicators
   - Ranks results by relevance

3. **RecommendationAgent**: Presents final recommendations
   - Formats results in a user-friendly format
   - Provides context and practical information
   - Handles follow-up questions

## Features

- **MCP Tool Integration**: Uses custom Mapbox MCP server for API access
- **Intelligent Search**: Understands natural language queries for cuisine, location, and preferences
- **Detailed Filtering**: Gets comprehensive place details including phone numbers, websites, and contact info
- **User-Friendly Presentation**: Clear, engaging recommendations with all relevant details

## Setup

### Prerequisites

- Google Cloud Project with Vertex AI enabled
- Mapbox API key (get one at [https://www.mapbox.com/](https://www.mapbox.com/))
- Python 3.11+

### Environment Variables

Set the following environment variables:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MAPBOX_API_KEY=your-mapbox-api-key
```

For local development, create a `.env` file in the project root:

```
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MAPBOX_API_KEY=your-mapbox-api-key
```

### Installation

```bash
pip install -r requirements.txt
```

## Usage

### Local Testing

```python
from restaurant_finder.agent import root_agent

# The agent is ready to use
# You can interact with it through the Vertex AI Agent SDK
```

### Deploy to Vertex AI Agent Engine

The agent includes configuration for deployment to Vertex AI Agent Engine:

1. Ensure `.agent_engine_config.json` is configured
2. Deploy using Google Cloud CLI or console

Configuration in `.agent_engine_config.json`:
```json
{
    "min_instances": 0,
    "max_instances": 1,
    "resource_limits": {"cpu": "4", "memory": "8Gi"}
}
```

## Mapbox MCP Server

The agent uses a custom MCP server ([mapbox_mcp_server.py](restaurant_finder/tools/mapbox_mcp_server.py)) that provides three tools:

### mapbox_search_places
Search for restaurants and places using various criteria.

**Parameters:**
- `query` (required): Search query (e.g., "pizza", "sushi", "italian restaurant")
- `location`: Location name (e.g., "San Francisco, CA")
- `latitude`, `longitude`: Coordinates (alternative to location)
- `radius`: Search radius in meters (default: 5000)
- `limit`: Maximum results (default: 10)

### mapbox_get_place_details
Get detailed information about a specific place.

**Parameters:**
- `mapbox_id` (required): Mapbox place ID

### mapbox_search_nearby
Find restaurants near specific coordinates.

**Parameters:**
- `latitude`, `longitude` (required): Coordinates
- `radius`: Search radius in meters (default: 2000)
- `limit`: Maximum results (default: 20)

## Example Queries

- "Find Italian restaurants near San Francisco"
- "I want pizza in New York under $20"
- "Show me highly-rated sushi restaurants within 1 mile of Times Square"
- "Find restaurants near 37.7749, -122.4194"
- "Looking for cheap Mexican food in Austin"

## Project Structure

```
restaurant_finder/
├── agent.py                          # Main entry point
├── setup.py                          # Environment setup
├── requirements.txt                  # Dependencies
├── .agent_engine_config.json        # Deployment config
├── tools/
│   ├── __init__.py
│   ├── mapbox_mcp.py                # MCP toolset integration
│   ├── mapbox_mcp_server.py         # Custom MCP server
│   └── mapbox_places.py             # Direct API module
└── agents/
    ├── __init__.py
    ├── main_restaurant_agent.py     # Main sequential agent
    └── sub_agents/
        ├── __init__.py
        ├── search_agent.py          # Restaurant search
        ├── filter_agent.py          # Result filtering
        └── recommendation_agent.py  # Final presentation
```

## API Keys

### Getting a Mapbox API Key

1. Go to [https://www.mapbox.com/](https://www.mapbox.com/)
2. Sign up or log in
3. Go to your account page
4. Create a new access token (or use the default token)
5. Set it as the `MAPBOX_API_KEY` environment variable

Note: Mapbox API has rate limits. Check their documentation for current limits.

## Development

### Making the MCP Server Executable

```bash
chmod +x restaurant_finder/tools/mapbox_mcp_server.py
```

### Testing the MCP Server

```bash
MAPBOX_API_KEY=your-key python restaurant_finder/tools/mapbox_mcp_server.py
```

## Troubleshooting

### "MAPBOX_API_KEY not found"
Make sure the environment variable is set or add it to your `.env` file.

### "GOOGLE_CLOUD_PROJECT not found"
Set the `GOOGLE_CLOUD_PROJECT` environment variable to your GCP project ID.

### MCP Server Connection Timeout
Increase the timeout in [mapbox_mcp.py](restaurant_finder/tools/mapbox_mcp.py#L40) if needed.

### API Rate Limits
Mapbox has rate limits. If you hit them, wait and try again or upgrade your API plan.

## License

MIT
