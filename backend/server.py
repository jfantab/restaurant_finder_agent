"""Flask backend API for Restaurant Finder Agent.

Supports two modes:
- Local mode (RUN_LOCAL=true): Runs the agent locally using google.adk.runners with SQL tools via stdio MCP
- Cloud mode (RUN_LOCAL=false): Connects to deployed Vertex AI agent
"""

import os
import sys
import json
import asyncio
import time
import re
import uuid
import tempfile
import traceback
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from google.genai import types

# Load environment variables
load_dotenv()

# Add parent directory to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React Native web app

# Session-based filter state storage
session_filter_states = {}  # {session_id: FilterState}
session_timestamps = {}     # {session_id: timestamp} for cleanup

# Configuration
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
agent_name = "restaurant_finder_agent"
run_local = os.getenv("RUN_LOCAL", "false").lower() == "true"

if not project_id:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file")

# Agent and runner references (initialized based on mode)
agent = None
local_runner = None
local_agent = None

if run_local:
    print("Starting in LOCAL mode...")
    from restaurant_finder.setup import setup_environment
    from restaurant_finder.agents.streamlined_restaurant_agent import create_streamlined_restaurant_agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    setup_environment()

    # Use streamlined restaurant agent directly (no router)
    local_agent = create_streamlined_restaurant_agent(use_cloud_mcp=False)
    local_runner = Runner(
        agent=local_agent,
        app_name="restaurant_finder_backend",
        session_service=InMemorySessionService()
    )
    print(f"Local agent initialized: {local_agent.name}")
    print("Using streamlined restaurant agent (direct, no router)")
else:
    print("Starting in CLOUD mode...")
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=project_id, location=location)
    agent = next(
        (a for a in agent_engines.list() if a.display_name == agent_name),
        None
    )
    if not agent:
        raise ValueError(f"Agent '{agent_name}' not found in Vertex AI. Please deploy it first.")
    print(f"Connected to deployed agent: {agent.resource_name}")

def cleanup_old_sessions():
    """Remove sessions older than 1 hour."""
    current_time = time.time()
    expired = [sid for sid, ts in session_timestamps.items()
               if current_time - ts > 3600]
    for sid in expired:
        if sid in session_filter_states:
            del session_filter_states[sid]
        if sid in session_timestamps:
            del session_timestamps[sid]
    if expired:
        print(f"[DEBUG] Cleaned up {len(expired)} expired sessions")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "mode": "local" if run_local else "cloud",
        "agent": local_agent.name if run_local else agent.display_name
    })

@app.route('/api/search', methods=['POST'])
def search_restaurants():
    """Search for restaurants based on user query and preferences.

    Expected JSON body:
    {
        "query": "Italian restaurants",
        "location": {"lat": 37.7749, "lng": -122.4194},
        "session_id": "optional-session-id-for-follow-ups",
        "preferences": {
            "cuisine": "Italian",
            "price_range": "$$",
            "dietary_restrictions": ["Vegetarian"]
        }
    }
    """
    try:
        # Import FilterState here to avoid circular imports
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from restaurant_finder.models.filter_state import FilterState

        # Clean up old sessions
        cleanup_old_sessions()

        data = request.json
        query = data.get('query', '')
        location = data.get('location')
        preferences = data.get('preferences', {})
        session_id = data.get('session_id')  # Client provides session_id for follow-ups

        # Get or create filter state for this session
        if session_id and session_id in session_filter_states:
            filter_state = session_filter_states[session_id]
            print(f"[DEBUG] Loaded existing filter state for session {session_id}: {filter_state.get_filter_summary()}")
        else:
            # Initialize from preferences and location
            filter_state = FilterState(
                latitude=location.get('lat') if location else None,
                longitude=location.get('lng') if location else None,
                location_name=preferences.get('location_name', 'Current location'),
                cuisine=preferences.get('cuisine'),
                radius_miles=preferences.get('distance', 5.0),
                dietary_restrictions=preferences.get('dietary_restrictions', []),
            )

            # Map price_range to max_price_level
            price_map = {'$': 1, '$$': 2, '$$$': 3, '$$$$': 4}
            if preferences.get('price_range'):
                filter_state.max_price_level = price_map.get(preferences['price_range'])

            print(f"[DEBUG] Created new filter state: {filter_state.get_filter_summary()}")

        # Build context with filter state
        context_parts = []

        # ALWAYS include location coordinates first (most important for search)
        if filter_state.latitude and filter_state.longitude:
            context_parts.append(f"User location: latitude {filter_state.latitude}, longitude {filter_state.longitude}")
        elif location:
            context_parts.append(f"User location: latitude {location['lat']}, longitude {location['lng']}")

        # Include filter state summary if filters are active
        filter_summary = filter_state.get_filter_summary()
        if filter_summary != "No filters":
            context_parts.append(f"Current filter state: {filter_summary}")

        if preferences.get('cuisine'):
            context_parts.append(f"Preferred cuisine: {preferences['cuisine']}")

        if preferences.get('price_range'):
            context_parts.append(f"Price range: {preferences['price_range']}")

        if preferences.get('dietary_restrictions'):
            context_parts.append(f"Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}")

        if preferences.get('distance'):
            context_parts.append(f"Search radius: {preferences['distance']} miles")

        context = "\n".join(context_parts) if context_parts else ""
        full_prompt = f"{context}\n\nUser request: {query}" if context else query

        print(f"[DEBUG] Full prompt being sent to agent:")
        print(f"[DEBUG] {full_prompt}")

        # Performance timing
        start_time = time.time()

        if run_local:
            # Local mode: Use the Runner to execute the agent
            response_text, used_session_id = asyncio.run(run_local_agent(full_prompt, session_id))
        else:
            # Cloud mode: Use async_stream_query for deployed ADK agents
            response_text = asyncio.run(get_cloud_response(full_prompt))
            used_session_id = session_id

        # Performance logging
        agent_time = time.time() - start_time
        print(f"[PERFORMANCE] Agent execution time: {agent_time:.2f}s")

        print(f"[DEBUG] Response text length: {len(response_text)}")
        print(f"[DEBUG] Response text first 300 chars: {response_text[:300]}")

        # Try to parse restaurant data from response
        parse_start = time.time()
        restaurants = extract_restaurants_from_response(response_text)
        parse_time = time.time() - parse_start
        print(f"[PERFORMANCE] JSON parsing time: {parse_time:.3f}s")

        # Extract summary from response
        summary = extract_summary_from_response(response_text)

        print(f"[DEBUG] Extracted {len(restaurants) if restaurants else 0} restaurants")
        print(f"[DEBUG] Summary: {summary[:100] if summary else 'None'}...")

        # Store filter state and update timestamp
        if used_session_id:
            session_filter_states[used_session_id] = filter_state
            session_timestamps[used_session_id] = time.time()

        return jsonify({
            "success": True,
            "response": summary or response_text,
            "restaurants": restaurants,
            "session_id": used_session_id,  # Return session_id for client to use in follow-ups
            "filter_state": {
                "summary": filter_state.get_filter_summary(),
                "filters": {
                    "cuisine": filter_state.cuisine,
                    "price_level": filter_state.max_price_level,
                    "rating": filter_state.min_rating,
                    "distance": filter_state.radius_miles,
                    "dietary": filter_state.dietary_restrictions,
                    "sort_by": filter_state.sort_by,
                }
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


async def run_local_agent(prompt: str, session_id: str = None) -> tuple[str, str]:
    """Run the local agent and return the response text.

    Args:
        prompt: The user prompt to send to the agent
        session_id: Optional session ID for conversation continuity.
                   If None, a new session is created.

    Returns:
        Tuple of (response_text, session_id)
    """
    user_id = "flask_user"

    # Use provided session_id or create a new one
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Try to get existing session, or create a new one
    try:
        session = await local_runner.session_service.get_session(
            app_name="restaurant_finder_backend",
            user_id=user_id,
            session_id=session_id
        )
        if session is None:
            raise ValueError("Session not found")
    except Exception as e:
        # Session doesn't exist or was invalidated (e.g., server restart), create a new one
        print(f"Session {session_id} not found, creating new session: {e}")
        # Generate a new session_id since the old one is invalid
        session_id = str(uuid.uuid4())
        session = await local_runner.session_service.create_session(
            app_name="restaurant_finder_backend",
            user_id=user_id,
            session_id=session_id
        )

    # Create the user message
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)]
    )

    # Run the agent and collect responses (use async version)
    last_response = None
    full_responses = []

    async for event in local_runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        # Debug: Log all events with authors
        if hasattr(event, 'author'):
            print(f"[DEBUG] Event from author: {event.author}")

        # Check for StreamlinedRestaurantAgent response (direct agent, no router)
        if hasattr(event, 'author') and event.author == 'StreamlinedRestaurantAgent':
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        last_response = part.text
                        print(f"[DEBUG] Found StreamlinedRestaurantAgent response: {part.text[:100]}")

        # Collect all text responses as fallback
        if hasattr(event, 'content') and event.content:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    full_responses.append(part.text)

    # Return the response
    print(f"[DEBUG] last_response: {last_response[:100] if last_response else 'None'}")
    print(f"[DEBUG] full_responses count: {len(full_responses)}")

    if last_response:
        print("[DEBUG] Returning last_response from StreamlinedRestaurantAgent")
        return last_response, session_id
    elif full_responses:
        print("[DEBUG] Returning last full_response")
        return full_responses[-1], session_id
    else:
        print("[ERROR] No response captured from agent!")
        return "No response from agent", session_id


async def get_cloud_response(prompt: str) -> str:
    """Get response from the deployed cloud agent.

    Args:
        prompt: The user prompt to send to the agent

    Returns:
        The final response text from the agent
    """
    last_recommendation_response = None
    full_trace = []

    async for event in agent.async_stream_query(
        user_id="react_user",
        message=prompt
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

@app.route('/api/stream-search', methods=['POST'])
def stream_search_restaurants():
    """Stream restaurant search results (supports both local and cloud modes)."""
    try:
        data = request.json
        query = data.get('query', '')
        location = data.get('location')
        preferences = data.get('preferences', {})
        session_id = data.get('session_id')  # Client provides session_id for follow-ups

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

        if preferences.get('distance'):
            context_parts.append(f"Search radius: {preferences['distance']} miles")

        context = "\n".join(context_parts) if context_parts else ""
        full_prompt = f"{context}\n\nUser request: {query}" if context else query

        def generate():
            """Generator function for streaming responses."""
            nonlocal session_id
            try:
                if run_local:
                    # Local mode: Use the Runner (async)
                    response_text, used_session_id = asyncio.run(run_local_agent(full_prompt, session_id))
                else:
                    # Cloud mode: Use async_stream_query
                    response_text = asyncio.run(get_cloud_response(full_prompt))
                    used_session_id = session_id

                restaurants = extract_restaurants_from_response(response_text)
                summary = extract_summary_from_response(response_text)

                result = {
                    "success": True,
                    "response": summary or response_text,
                    "restaurants": restaurants,
                    "session_id": used_session_id  # Return session_id for client to use in follow-ups
                }

                yield f"data: {json.dumps(result)}\n\n"

            except Exception as e:
                traceback.print_exc()
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

def normalize_json_quotes(text):
    """Replace curly/smart quotes with straight ASCII quotes.

    This fixes JSON parsing issues when the LLM outputs curly quotes
    instead of standard ASCII double quotes.

    Args:
        text: The text containing potential curly quotes

    Returns:
        Text with all quotes normalized to ASCII
    """
    replacements = {
        '"': '"', '"': '"',  # Double curly quotes
        ''': "'", ''': "'",  # Single curly quotes
        '「': '"', '」': '"',  # CJK quotes
        '『': '"', '』': '"',  # CJK double quotes
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def fix_invalid_json_escapes(text):
    r"""Fix invalid JSON escape sequences.

    JSON only allows these escape sequences: \" \\ \/ \b \f \n \r \t \uXXXX
    LLMs sometimes output invalid escapes like \' which breaks JSON parsing.

    Args:
        text: The JSON text with potential invalid escapes

    Returns:
        Text with invalid escapes fixed
    """
    text = re.sub(r"(?<!\\)\\'", "'", text)
    text = re.sub(r'\\([^"\\/bfnrtu])', r'\1', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
    return text


def extract_restaurants_from_response(response_text):
    """Extract restaurant data from agent response.

    Args:
        response_text: The full text response from the agent

    Returns:
        List of restaurant dictionaries or None
    """
    # Normalize quotes and fix invalid escapes before processing
    response_text = normalize_json_quotes(response_text)
    response_text = fix_invalid_json_escapes(response_text)

    print(f"[DEBUG] extract_restaurants_from_response called with {len(response_text)} chars")
    print(f"[DEBUG] First 200 chars: {response_text[:200]}")

    data = None

    try:
        # First, try to parse the whole response as JSON directly
        try:
            data = json.loads(response_text, strict=False)
            print(f"[DEBUG] Parsed entire response as JSON, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        except json.JSONDecodeError:
            print("[DEBUG] Could not parse entire response as JSON, trying to extract...")

        # If direct parsing didn't work, try to find JSON in the response
        if data is None:
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                print(f"[DEBUG] Found JSON in code block")
            else:
                # Try to find raw JSON object
                start_idx = response_text.find('{')
                if start_idx != -1:
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
                        # No matching closing brace found, this is plain text
                        print("[DEBUG] No matching closing brace found, treating as plain text response")
                        return None
                else:
                    # No JSON object found at all, this is plain text
                    print("[DEBUG] No JSON object found, treating as plain text response")
                    return None

            # Parse the extracted JSON (use strict=False to handle control characters)
            try:
                data = json.loads(json_text, strict=False)
                print(f"[DEBUG] Parsed extracted JSON, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON parse error: {e}")
                print(f"[DEBUG] Problematic JSON around char {e.pos}: {json_text[max(0, e.pos-100):min(len(json_text), e.pos+100)]}")
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                    f.write(json_text)
                    print(f"[DEBUG] Full JSON saved to: {f.name}")
                # This is plain text, not JSON - return None gracefully
                print("[DEBUG] Returning None for plain text response")
                return None

        # Handle agent response wrappers
        # Try to unwrap agent-name-based wrappers like {"StreamlinedRestaurantAgent_response": {...}}
        if isinstance(data, dict) and len(data) == 1:
            key = list(data.keys())[0]
            if key.endswith('_response') or key.endswith('Agent_response'):
                print(f"[DEBUG] Found agent response wrapper: {key}")
                data = data[key]
                print(f"[DEBUG] Unwrapped data, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")

        # Handle nested router response: {"restaurant_finder_response": {"result": "<JSON string>"}}
        if isinstance(data, dict) and 'restaurant_finder_response' in data:
            print("[DEBUG] Found restaurant_finder_response wrapper")
            result = data['restaurant_finder_response'].get('result', '')
            print(f"[DEBUG] Result type: {type(result)}, first 100 chars: {str(result)[:100]}")
            if isinstance(result, str):
                # Parse the nested JSON string (use strict=False for control characters)
                try:
                    data = json.loads(result, strict=False)
                    print(f"[DEBUG] Parsed nested JSON, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                except json.JSONDecodeError as e:
                    print(f"[DEBUG] Nested JSON parse error: {e}")
                    print(f"[DEBUG] Problematic JSON around char {e.pos}: {result[max(0, e.pos-100):min(len(result), e.pos+100)]}")
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                        f.write(result)
                        print(f"[DEBUG] Full nested JSON saved to: {f.name}")
                    raise
            elif isinstance(result, dict):
                data = result

        # Handle direct {"result": "<JSON string>"} wrapper from after_tool_callback
        if isinstance(data, dict) and 'result' in data and len(data) == 1:
            print("[DEBUG] Found result wrapper from after_tool_callback")
            result = data['result']
            print(f"[DEBUG] Result type: {type(result)}, first 100 chars: {str(result)[:100]}")
            if isinstance(result, str):
                try:
                    data = json.loads(result, strict=False)
                    print(f"[DEBUG] Parsed result JSON, keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                except json.JSONDecodeError:
                    print("[DEBUG] Could not parse result as JSON")
            elif isinstance(result, dict):
                data = result

        # Extract restaurants array
        if isinstance(data, dict) and 'restaurants' in data and isinstance(data['restaurants'], list):
            print(f"[DEBUG] Found {len(data['restaurants'])} restaurants in response")
            restaurants = []
            for restaurant in data['restaurants']:
                # Only include restaurants that have coordinates
                if restaurant.get('latitude') and restaurant.get('longitude'):
                    # Extract reviews if available
                    reviews = []
                    if restaurant.get('reviews'):
                        for review in restaurant['reviews']:  # Include all reviews
                            reviews.append({
                                'author': review.get('author', 'Anonymous'),
                                'rating': review.get('rating'),
                                'text': review.get('text', '')
                            })

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
                        'description': restaurant.get('description', ''),
                        'review_summary': restaurant.get('review_summary', ''),
                        'reviews': reviews if reviews else None
                    })
            print(f"[DEBUG] Extracted {len(restaurants)} restaurants with coordinates")
            return restaurants if restaurants else None
        else:
            print(f"[DEBUG] No restaurants array found in data")
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing restaurant data: {e}")
        traceback.print_exc()
        return None

    return None

def extract_summary_from_response(response_text):
    """Extract summary from agent response.

    Args:
        response_text: The full text response from the agent

    Returns:
        Summary string or None
    """
    # Normalize quotes and fix invalid escapes before processing
    response_text = normalize_json_quotes(response_text)
    response_text = fix_invalid_json_escapes(response_text)

    data = None

    try:
        # First, try to parse the whole response as JSON directly
        try:
            data = json.loads(response_text, strict=False)
        except json.JSONDecodeError:
            pass

        # If direct parsing didn't work, try to find JSON in the response
        if data is None:
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find raw JSON object
                start_idx = response_text.find('{')
                if start_idx != -1:
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

            # Parse the extracted JSON (use strict=False to handle control characters)
            data = json.loads(json_text, strict=False)

        # Handle agent response wrappers
        # Try to unwrap agent-name-based wrappers like {"StreamlinedRestaurantAgent_response": {...}}
        if isinstance(data, dict) and len(data) == 1:
            key = list(data.keys())[0]
            if key.endswith('_response') or key.endswith('Agent_response'):
                data = data[key]

        # Handle nested router response: {"restaurant_finder_response": {"result": "<JSON string>"}}
        if isinstance(data, dict) and 'restaurant_finder_response' in data:
            result = data['restaurant_finder_response'].get('result', '')
            if isinstance(result, str):
                # Parse the nested JSON string (use strict=False for control characters)
                data = json.loads(result, strict=False)
            elif isinstance(result, dict):
                data = result

        # Handle direct {"result": "<JSON string>"} wrapper from after_tool_callback
        if isinstance(data, dict) and 'result' in data and len(data) == 1:
            result = data['result']
            if isinstance(result, str):
                try:
                    data = json.loads(result, strict=False)
                except json.JSONDecodeError:
                    pass
            elif isinstance(result, dict):
                data = result

        # Extract summary
        if isinstance(data, dict) and 'summary' in data:
            return data['summary']

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing summary: {e}")
        return None

    return None

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=True)
