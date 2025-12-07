"""Flask backend API for Restaurant Finder Agent."""

import os
import json
import asyncio
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Vertex AI modules
import vertexai
from vertexai import agent_engines

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React Native web app

# Initialize Vertex AI and connect to deployed agent
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
agent_name = "restaurant_finder_agent"

if not project_id:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file")

# Initialize Vertex AI
vertexai.init(project=project_id, location=location)

# Find the deployed agent
agents_list = list(agent_engines.list())
deployed_agent = next(
    (agent for agent in agents_list if agent.display_name == agent_name),
    None
)

if not deployed_agent:
    raise ValueError(f"Agent '{agent_name}' not found in Vertex AI. Please deploy it first.")

agent = deployed_agent
print(f"✓ Connected to deployed agent: {deployed_agent.resource_name}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "agent": "initialized"})

@app.route('/api/search', methods=['POST'])
def search_restaurants():
    """Search for restaurants based on user query and preferences.

    Expected JSON body:
    {
        "query": "Italian restaurants",
        "location": {"lat": 37.7749, "lng": -122.4194},
        "preferences": {
            "cuisine": "Italian",
            "price_range": "$$",
            "dietary_restrictions": ["Vegetarian"]
        }
    }
    """
    try:
        data = request.json
        query = data.get('query', '')
        location = data.get('location')
        preferences = data.get('preferences', {})

        # Build context with preferences
        context_parts = []

        if location:
            context_parts.append(f"Current location: latitude {location['lat']}, longitude {location['lng']}")

        if preferences.get('cuisine'):
            context_parts.append(f"Preferred cuisine: {preferences['cuisine']}")

        if preferences.get('price_range'):
            context_parts.append(f"Price range: {preferences['price_range']}")

        if preferences.get('dietary_restrictions'):
            context_parts.append(f"Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}")

        context = "\n".join(context_parts) if context_parts else ""
        full_prompt = f"{context}\n\nUser request: {query}" if context else query

        # Use async_stream_query for deployed ADK agents
        async def get_response():
            last_recommendation_response = None
            full_trace = []

            async for event in agent.async_stream_query(
                user_id="react_user",
                message=full_prompt
            ):
                # Store full trace for debugging
                full_trace.append(str(event))

                # Check if this is the final recommendation agent response
                if isinstance(event, dict):
                    if event.get('author') == 'RestaurantRecommendationAgent':
                        content = event.get('content', {})
                        parts = content.get('parts', [])
                        for part in parts:
                            if 'text' in part:
                                last_recommendation_response = part['text']

            # Return the final recommendation or the full trace
            if last_recommendation_response:
                return last_recommendation_response
            else:
                return "\n".join(full_trace) if full_trace else "No response"

        # Run async function
        response_text = asyncio.run(get_response())

        # Try to parse restaurant data from response
        restaurants = extract_restaurants_from_response(response_text)

        # Extract summary from response
        summary = extract_summary_from_response(response_text)

        return jsonify({
            "success": True,
            "response": summary or response_text,
            "restaurants": restaurants
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/stream-search', methods=['POST'])
def stream_search_restaurants():
    """Stream restaurant search results (for deployed agents)."""
    try:
        data = request.json
        query = data.get('query', '')
        location = data.get('location')
        preferences = data.get('preferences', {})

        # Build context with preferences
        context_parts = []

        if location:
            context_parts.append(f"Current location: latitude {location['lat']}, longitude {location['lng']}")

        if preferences.get('cuisine'):
            context_parts.append(f"Preferred cuisine: {preferences['cuisine']}")

        if preferences.get('price_range'):
            context_parts.append(f"Price range: {preferences['price_range']}")

        if preferences.get('dietary_restrictions'):
            context_parts.append(f"Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}")

        context = "\n".join(context_parts) if context_parts else ""
        full_prompt = f"{context}\n\nUser request: {query}" if context else query

        def generate():
            """Generator function for streaming responses."""
            try:
                # For deployed agents, use async_stream_query
                import asyncio

                async def stream_response():
                    last_recommendation_response = None

                    async for event in agent.async_stream_query(
                        user_id="react_user",
                        message=full_prompt
                    ):
                        # Check if this is the final recommendation agent response
                        if isinstance(event, dict):
                            if event.get('author') == 'RestaurantRecommendationAgent':
                                content = event.get('content', {})
                                parts = content.get('parts', [])
                                for part in parts:
                                    if 'text' in part:
                                        last_recommendation_response = part['text']

                    return last_recommendation_response

                response_text = asyncio.run(stream_response())
                restaurants = extract_restaurants_from_response(response_text)

                result = {
                    "success": True,
                    "response": response_text,
                    "restaurants": restaurants
                }

                yield f"data: {json.dumps(result)}\n\n"

            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_result)}\n\n"

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def extract_restaurants_from_response(response_text):
    """Extract restaurant data from agent response.

    Args:
        response_text: The full text response from the agent

    Returns:
        List of restaurant dictionaries or None
    """
    import re

    try:
        # Try to find JSON in the response
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON object
            start_idx = response_text.find('{')
            if start_idx != -1 and '"restaurants"' in response_text[start_idx:]:
                # Find the matching closing brace
                brace_count = 0
                in_string = False
                escape_next = False

                for i in range(start_idx, len(response_text)):
                    char = response_text[i]

                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"':
                        in_string = not in_string
                        continue

                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_text = response_text[start_idx:i+1]
                                break
                else:
                    json_text = response_text
            else:
                json_text = response_text

        # Parse the JSON
        data = json.loads(json_text)

        # Extract restaurants array
        if 'restaurants' in data and isinstance(data['restaurants'], list):
            restaurants = []
            for restaurant in data['restaurants']:
                # Only include restaurants that have coordinates
                if restaurant.get('latitude') and restaurant.get('longitude'):
                    restaurants.append({
                        'name': restaurant.get('name', 'Unknown'),
                        'address': restaurant.get('address', ''),
                        'latitude': float(restaurant['latitude']),
                        'longitude': float(restaurant['longitude']),
                        'cuisine_type': restaurant.get('cuisine_type', ''),
                        'rating': restaurant.get('rating'),
                        'price_level': restaurant.get('price_level', ''),
                        'distance_miles': restaurant.get('distance_miles'),
                        'phone': restaurant.get('phone', ''),
                        'website': restaurant.get('website', ''),
                        'description': restaurant.get('description', '')
                    })
            return restaurants if restaurants else None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing restaurant data: {e}")
        return None

    return None

def extract_summary_from_response(response_text):
    """Extract summary from agent response.

    Args:
        response_text: The full text response from the agent

    Returns:
        Summary string or None
    """
    import re

    try:
        # Try to find JSON in the response
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON object
            start_idx = response_text.find('{')
            if start_idx != -1 and '"restaurants"' in response_text[start_idx:]:
                # Find the matching closing brace
                brace_count = 0
                in_string = False
                escape_next = False

                for i in range(start_idx, len(response_text)):
                    char = response_text[i]

                    if escape_next:
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        continue

                    if char == '"':
                        in_string = not in_string
                        continue

                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_text = response_text[start_idx:i+1]
                                break
                else:
                    json_text = response_text
            else:
                json_text = response_text

        # Parse the JSON
        data = json.loads(json_text)

        # Extract summary
        if 'summary' in data:
            return data['summary']

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing summary: {e}")
        return None

    return None

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=True)
