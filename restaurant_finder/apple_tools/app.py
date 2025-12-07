"""Server wrapper to run Apple Maps MCP with both SSE and REST endpoints.

This server exposes:
- /sse - MCP protocol endpoint for local development
- /api/* - REST endpoints for Vertex AI FunctionTools
"""

import os
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from apple_maps_mcp import mcp, search_places, get_place_details, geocode_address


# REST API routes for Vertex AI FunctionTools
async def api_search_places(request):
    """REST endpoint for search_places tool."""
    try:
        data = await request.json()
        query = data.get("query")
        limit = data.get("limit", 5)

        if not query:
            return JSONResponse(
                {"error": "Missing required parameter: query"},
                status_code=400
            )

        result = search_places(query, limit)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"},
            status_code=500
        )


async def api_get_place_details(request):
    """REST endpoint for get_place_details tool."""
    try:
        data = await request.json()
        place_name = data.get("place_name")
        address = data.get("address")

        if not place_name or not address:
            return JSONResponse(
                {"error": "Missing required parameters: place_name and address"},
                status_code=400
            )

        result = get_place_details(place_name, address)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"},
            status_code=500
        )


async def api_geocode_address(request):
    """REST endpoint for geocode_address tool."""
    try:
        data = await request.json()
        address = data.get("address")

        if not address:
            return JSONResponse(
                {"error": "Missing required parameter: address"},
                status_code=400
            )

        result = geocode_address(address)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"},
            status_code=500
        )


async def health_check(request):
    """Health check endpoint for Cloud Run."""
    return JSONResponse({"status": "healthy"})


# Combine SSE (MCP) and REST (FunctionTools) endpoints
app = Starlette(routes=[
    # MCP SSE endpoint for local development
    Mount("/sse", app=mcp.sse_app),

    # REST API endpoints for Vertex AI
    Route("/api/search_places", api_search_places, methods=["POST"]),
    Route("/api/get_place_details", api_get_place_details, methods=["POST"]),
    Route("/api/geocode_address", api_geocode_address, methods=["POST"]),

    # Health check for Cloud Run
    Route("/health", health_check, methods=["GET"]),
])
