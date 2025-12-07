"""Streamlit chat interface for Restaurant Finder Agent."""

import streamlit as st
import os
import json
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import agent modules
try:
    import vertexai
    from vertexai import agent_engines
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.info("""
    **How to run this app:**

    Make sure you're in the restaurant_finder directory:
    ```bash
    cd /Users/johnlu/Documents/kaggle_agents/restaurant_finder
    streamlit run streamlit.py
    ```

    **Verify dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    """)
    st.stop()

# Initialize session state
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'agent_initialized' not in st.session_state:
    st.session_state.agent_initialized = False
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {
        'cuisine': '',
        'price_range': '',
        'dietary_restrictions': [],
        'location': None
    }
if 'current_restaurants' not in st.session_state:
    st.session_state.current_restaurants = None
if 'map_loaded' not in st.session_state:
    st.session_state.map_loaded = False
if 'last_sent_restaurants' not in st.session_state:
    st.session_state.last_sent_restaurants = None

def initialize_agent():
    """Initialize connection to the deployed Vertex AI agent."""
    try:
        with st.spinner("Connecting to Vertex AI Agent..."):
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-west1")
            agent_name = "restaurant_finder_agent"

            if not project_id:
                return False, "GOOGLE_CLOUD_PROJECT not set in .env file"

            # Initialize Vertex AI
            vertexai.init(project=project_id, location=location)

            # Find the deployed agent
            agents_list = list(agent_engines.list())
            deployed_agent = next(
                (agent for agent in agents_list if agent.display_name == agent_name),
                None
            )

            if not deployed_agent:
                return False, f"Agent '{agent_name}' not found in Vertex AI. Please deploy it first."

            st.session_state.agent = deployed_agent
            st.session_state.agent_initialized = True
            return True, f"Connected to deployed agent: {deployed_agent.resource_name}"

    except Exception as e:
        return False, f"Error connecting to deployed agent: {str(e)}"

def format_preferences() -> str:
    """Format user preferences as a string for context."""
    prefs = st.session_state.user_preferences
    pref_parts = []

    if prefs['cuisine']:
        pref_parts.append(f"Cuisine: {prefs['cuisine']}")
    if prefs['price_range']:
        pref_parts.append(f"Price: {prefs['price_range']}")
    if prefs['dietary_restrictions']:
        pref_parts.append(f"Dietary: {', '.join(prefs['dietary_restrictions'])}")
    if prefs['location']:
        pref_parts.append(f"Location: {prefs['location']['lat']:.4f}, {prefs['location']['lng']:.4f}")

    return " | ".join(pref_parts) if pref_parts else "No preferences set"

def display_chat_message(message: Dict[str, str]):
    """Display a chat message."""
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def extract_restaurants_from_response(response_text: str) -> Optional[List[Dict]]:
    """Extract restaurant data from agent response.

    The recommendation agent returns JSON with restaurant details including coordinates.
    This function parses that JSON and extracts the restaurant list.

    Args:
        response_text: The full text response from the agent

    Returns:
        List of restaurant dictionaries with name, address, lat, lng, etc., or None if parsing fails
    """
    try:
        # Try to find JSON in the response (it might be wrapped in markdown code blocks)
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find raw JSON object - use balanced brace matching
            # Look for opening brace followed by "restaurants" key
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
                    # If we didn't find a closing brace, try the whole thing
                    json_text = response_text
            else:
                # Maybe the entire response is JSON
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
                        'description': restaurant.get('description', '')
                    })
            return restaurants if restaurants else None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error parsing restaurant data: {e}")
        return None

    return None

def format_user_friendly_response(response_text: str, restaurants: Optional[List[Dict]]) -> str:
    """Format the raw agent response into a user-friendly message.

    Args:
        response_text: The raw response from the agent
        restaurants: Extracted restaurant data if available

    Returns:
        Formatted response text for display (summary only, details in map popups)
    """
    if not restaurants:
        # If no restaurants found, return the raw response
        return response_text

    # Try to extract the summary and additional notes from the JSON
    try:
        # Use the same extraction logic as extract_restaurants_from_response
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
        summary = data.get('summary', '')
        additional_notes = data.get('additional_notes', '')

        # Build concise response with only summary
        response_parts = []

        if summary:
            response_parts.append(f"{summary}")

        if additional_notes:
            response_parts.append(f"\n**Tips:** {additional_notes}")

        # Add note about map markers
        response_parts.append(f"\n*Found {len(restaurants)} restaurant(s). Click the markers on the map to see details.*")

        return '\n'.join(response_parts)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error formatting response: {e}")
        print(f"Response text (first 500 chars): {response_text[:500]}")

    # Fallback - just show count and instruction
    return f"*Found {len(restaurants)} restaurant(s). Click the markers on the map to see details.*"

def send_markers_to_map(restaurants: List[Dict]):
    """Send restaurant markers to the MapKit JS iframe.

    Args:
        restaurants: List of restaurant dictionaries with coordinates
    """
    if not restaurants:
        return

    # Create JavaScript to send markers to the map iframe with better error handling
    markers_js = """
    <script>
        (function() {
            console.log('send_markers_to_map: Starting marker injection');
            const restaurants = """ + json.dumps(restaurants) + """;
            console.log('send_markers_to_map: Found', restaurants.length, 'restaurants');

            // Function to try finding and messaging the iframe
            function sendMarkersToIframe(attempts) {
                if (attempts <= 0) {
                    console.error('send_markers_to_map: Failed to find map iframe after multiple attempts');
                    return;
                }

                // Try multiple ways to find the iframe
                const iframes = window.parent.document.getElementsByTagName('iframe');
                let mapIframe = null;

                // Look for iframe with map content
                for (let i = 0; i < iframes.length; i++) {
                    const iframe = iframes[i];
                    const src = iframe.src || '';

                    // Skip this script's own iframe
                    if (iframe === window.frameElement) continue;

                    // First iframe that's not us is likely the map
                    if (!mapIframe) {
                        mapIframe = iframe;
                        console.log('send_markers_to_map: Found potential map iframe at index', i);
                    }
                }

                if (!mapIframe) {
                    console.log('send_markers_to_map: Map iframe not found, retrying...', attempts - 1);
                    setTimeout(function() { sendMarkersToIframe(attempts - 1); }, 500);
                    return;
                }

                try {
                    console.log('send_markers_to_map: Sending clearRestaurantMarkers message');
                    mapIframe.contentWindow.postMessage({
                        type: 'clearRestaurantMarkers'
                    }, '*');

                    // Send each restaurant as a marker with full data
                    restaurants.forEach(function(restaurant, index) {
                        setTimeout(function() {
                            console.log('send_markers_to_map: Adding marker for', restaurant.name, 'at', restaurant.latitude, restaurant.longitude);

                            mapIframe.contentWindow.postMessage({
                                type: 'addRestaurantMarker',
                                restaurant: restaurant  // Send entire restaurant object
                            }, '*');
                        }, index * 100 + 200); // Wait a bit longer for map to be ready
                    });

                    // Center map to show all restaurants
                    if (restaurants.length > 0) {
                        setTimeout(function() {
                            console.log('send_markers_to_map: Fitting map to show all restaurants');
                            mapIframe.contentWindow.postMessage({
                                type: 'fitToShowRestaurants',
                                restaurants: restaurants
                            }, '*');
                        }, restaurants.length * 100 + 500);
                    }
                } catch (e) {
                    console.error('send_markers_to_map: Error sending messages to iframe:', e);
                }
            }

            // Start trying to send markers with retries after a delay
            // Wait for map to be fully loaded
            setTimeout(function() {
                sendMarkersToIframe(10);
            }, 1000); // Initial 1 second delay for map to load
        })();
    </script>
    """

    # Inject the JavaScript
    # Note: st.components.v1.html doesn't support keys, so the script runs on every render
    # The 1-second delay and retry logic handle timing issues
    st.components.v1.html(markers_js, height=0)

def generate_mapkit_token():
    """Generate JWT token for MapKit JS authentication."""
    import jwt
    import time
    from pathlib import Path

    team_id = os.getenv("APPLE_TEAM_ID", "").strip('"')
    key_id = os.getenv("APPLE_KEY_ID", "").strip('"')

    if not all([team_id, key_id]):
        return None

    # Try to read the private key from the .p8 file
    key_file = Path(__file__).parent / f"AuthKey_{key_id}.p8"

    if not key_file.exists():
        print(f"Error: Private key file not found: {key_file}")
        return None

    try:
        with open(key_file, 'r') as f:
            private_key = f.read()
    except Exception as e:
        print(f"Error reading private key file: {e}")
        return None

    # Token expires in 1 hour
    expiration_time = int(time.time()) + 3600

    headers = {
        "kid": key_id,
        "typ": "JWT",
        "alg": "ES256"
    }

    payload = {
        "iss": team_id,
        "iat": int(time.time()),
        "exp": expiration_time
    }

    try:
        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        return token
    except Exception as e:
        print(f"Error generating MapKit token: {e}")
        return None

def create_mapkit_html():
    """Create HTML for MapKit JS integration."""
    # Generate MapKit token
    mapkit_token = generate_mapkit_token()

    if not mapkit_token:
        return "<div style='padding: 20px; color: red;'>Error: MapKit credentials not configured. Please set APPLE_TEAM_ID, APPLE_KEY_ID, and APPLE_PRIVATE_KEY in your .env file.</div>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.apple-mapkit.com/mk/5.x.x/mapkit.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                height: 100vh;
                overflow: hidden;
            }}
            #map {{
                width: 100%;
                height: 100%;
            }}
            #location-button {{
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: white;
                border: none;
                border-radius: 8px;
                padding: 10px 15px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                cursor: pointer;
                font-size: 20px;
                transition: background-color 0.2s;
            }}
            #location-button:hover {{
                background-color: #f0f0f0;
            }}
            #location-button:active {{
                background-color: #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <button id="location-button" title="Get Current Location">📍</button>
        <div id="map"></div>
        <script>
            var map;
            var userLocationAnnotation;
            var restaurantAnnotations = [];

            // Wait for MapKit to load
            window.addEventListener('DOMContentLoaded', function() {{
                if (typeof mapkit === 'undefined') {{
                    console.error('MapKit JS failed to load');
                    document.getElementById('map').innerHTML = '<div style="padding: 20px; color: red;">MapKit JS failed to load. Please check your internet connection.</div>';
                    return;
                }}

                mapkit.init({{
                    authorizationCallback: function(done) {{
                        done('{mapkit_token}');
                    }}
                }});

            // Create the map
            map = new mapkit.Map("map", {{
                center: new mapkit.Coordinate(37.7749, -122.4194), // San Francisco
                zoom: 12,
                colorScheme: mapkit.Map.ColorSchemes.Light,
                showsCompass: mapkit.FeatureVisibility.Adaptive,
                showsMapTypeControl: false,
                showsZoomControl: true,
                showsUserLocationControl: true,
                showsPointsOfInterest: true
            }});

                // Function to get and show user's current location
                function getUserLocation() {{
                    if (!navigator.geolocation) {{
                        alert('Geolocation is not supported by your browser');
                        return;
                    }}

                    document.getElementById('location-button').textContent = '⌛';

                    navigator.geolocation.getCurrentPosition(
                        function(position) {{
                            var lat = position.coords.latitude;
                            var lng = position.coords.longitude;
                            var coordinate = new mapkit.Coordinate(lat, lng);

                            // Center map on user location
                            map.setCenterAnimated(coordinate, true);
                            map.region = new mapkit.CoordinateRegion(
                                coordinate,
                                new mapkit.CoordinateSpan(0.05, 0.05)
                            );

                            // Remove existing user location marker if any
                            if (userLocationAnnotation) {{
                                map.removeAnnotation(userLocationAnnotation);
                            }}

                            // Add a marker for user location
                            userLocationAnnotation = new mapkit.MarkerAnnotation(coordinate, {{
                                title: "Your Location",
                                color: "#007AFF",
                                glyphText: "📍"
                            }});
                            map.addAnnotation(userLocationAnnotation);

                            // Store location in sessionStorage for Streamlit to access
                            try {{
                                window.parent.sessionStorage.setItem('userLocation', JSON.stringify({{
                                    lat: lat,
                                    lng: lng,
                                    timestamp: Date.now()
                                }}));
                            }} catch(e) {{
                                console.log('Could not store location in parent storage:', e);
                            }}

                            document.getElementById('location-button').textContent = '📍';
                        }},
                        function(error) {{
                            console.error('Error getting location:', error);
                            alert('Unable to get your location. Please enable location services.');
                            document.getElementById('location-button').textContent = '📍';
                        }},
                        {{
                            enableHighAccuracy: true,
                            timeout: 5000,
                            maximumAge: 0
                        }}
                    );
                }}

                // Add click event to location button
                document.getElementById('location-button').addEventListener('click', getUserLocation);

                // Automatically get user location on load
                getUserLocation();

                // Listen for messages from parent window to update map
                window.addEventListener('message', function(event) {{
                    console.log('MapKit: Received message', event.data.type);

                    // Add restaurant marker with custom callout
                    if (event.data.type === 'addRestaurantMarker') {{
                        var restaurant = event.data.restaurant;
                        console.log('MapKit: Adding restaurant marker:', restaurant.name, 'at', restaurant.latitude, restaurant.longitude);

                        var coordinate = new mapkit.Coordinate(
                            restaurant.latitude,
                            restaurant.longitude
                        );

                        var annotation = new mapkit.MarkerAnnotation(coordinate, {{
                            title: restaurant.name,
                            subtitle: restaurant.address || '',
                            color: "#FF3B30",  // Red color for restaurants
                            glyphText: "🍴",
                            data: restaurant  // Store full restaurant data
                        }});

                        // Create custom callout content
                        var callout = {{
                            calloutElementForAnnotation: function(annotation) {{
                                var div = document.createElement('div');
                                div.style.cssText = 'padding: 15px; max-width: 300px; font-family: -apple-system, system-ui, sans-serif; background-color: white; border-radius: 8px;';

                                var data = annotation.data;
                                var html = '<div style="margin-bottom: 10px;">';
                                html += '<strong style="font-size: 16px;">' + data.name + '</strong>';
                                html += '</div>';

                                // Add properties in a structured way
                                var properties = [];
                                if (data.cuisine_type) properties.push(['Cuisine', data.cuisine_type]);
                                if (data.distance_miles) properties.push(['Distance', data.distance_miles.toFixed(1) + ' miles']);
                                if (data.address) properties.push(['Address', data.address]);
                                if (data.description) properties.push(['Description', data.description]);

                                properties.forEach(function(prop) {{
                                    html += '<div style="margin: 5px 0; font-size: 13px;">';
                                    html += '<span style="color: #666;">' + prop[0] + ':</span> ';
                                    html += '<span style="color: #000;">' + prop[1] + '</span>';
                                    html += '</div>';
                                }});

                                div.innerHTML = html;
                                return div;
                            }}
                        }};

                        annotation.callout = callout;
                        restaurantAnnotations.push(annotation);
                        map.addAnnotation(annotation);
                    }}

                    // Clear only restaurant markers, keep user location
                    if (event.data.type === 'clearRestaurantMarkers') {{
                        restaurantAnnotations.forEach(function(annotation) {{
                            map.removeAnnotation(annotation);
                        }});
                        restaurantAnnotations = [];
                    }}

                    // Fit map to show all restaurants
                    if (event.data.type === 'fitToShowRestaurants') {{
                        var allAnnotations = restaurantAnnotations.slice();
                        if (userLocationAnnotation) {{
                            allAnnotations.push(userLocationAnnotation);
                        }}
                        if (allAnnotations.length > 0) {{
                            map.showItems(allAnnotations, {{
                                animate: true,
                                padding: new mapkit.Padding(50, 50, 50, 50)
                            }});
                        }}
                    }}

                    // Legacy support for old marker types
                    if (event.data.type === 'addMarker') {{
                        var coordinate = new mapkit.Coordinate(
                            event.data.latitude,
                            event.data.longitude
                        );
                        var annotation = new mapkit.MarkerAnnotation(coordinate, {{
                            title: event.data.title,
                            subtitle: event.data.subtitle,
                            color: "#c969e0"
                        }});
                        map.addAnnotation(annotation);
                    }}

                    if (event.data.type === 'setCenter') {{
                        var coordinate = new mapkit.Coordinate(
                            event.data.latitude,
                            event.data.longitude
                        );
                        map.setCenterAnimated(coordinate);
                    }}

                    if (event.data.type === 'clearMarkers') {{
                        map.removeAnnotations(map.annotations);
                        restaurantAnnotations = [];
                        userLocationAnnotation = null;
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """
    return html_content

def main():
    st.set_page_config(
        page_title="Restaurant Finder Chat",
        page_icon="🍽️",
        layout="wide"
    )

    st.title("🍽️ Restaurant Finder AI Assistant")

    # Auto-initialize agent on first run
    if not st.session_state.agent_initialized:
        success, message = initialize_agent()
        if not success:
            st.error(f"Failed to initialize agent: {message}")
            st.stop()

    # Sidebar for preferences and controls
    with st.sidebar:
        st.header("Preferences")

        # Cuisine preference
        cuisine = st.selectbox(
            "Cuisine Type",
            ["Any", "Italian", "Japanese", "Mexican", "Chinese", "French",
             "Indian", "American", "Mediterranean", "Thai", "Korean"],
            index=0
        )
        if cuisine != "Any":
            st.session_state.user_preferences['cuisine'] = cuisine
        else:
            st.session_state.user_preferences['cuisine'] = ""

        # Price range
        price = st.select_slider(
            "Price Range",
            options=["Any", "$", "$$", "$$$", "$$$$"],
            value="Any"
        )
        if price != "Any":
            st.session_state.user_preferences['price_range'] = price
        else:
            st.session_state.user_preferences['price_range'] = ""

        # Dietary restrictions
        dietary = st.multiselect(
            "Dietary Restrictions",
            ["Vegetarian", "Vegan", "Gluten-Free", "Halal", "Kosher"]
        )
        st.session_state.user_preferences['dietary_restrictions'] = dietary

        st.markdown("---")

        # Display current preferences
        st.markdown("**Current Preferences:**")
        st.caption(format_preferences())

        st.markdown("---")

        # Chat controls
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.markdown("### About")
        st.info(
            "AI-powered restaurant finder using Google's Agent Development Kit "
            "with Apple Maps integration for real-time restaurant data."
        )

    # Split main screen into two columns
    col1, col2 = st.columns(2)

    # Left column - Apple Maps
    with col1:
        st.subheader("Map")

        # Display current location if available
        if st.session_state.user_preferences['location']:
            loc = st.session_state.user_preferences['location']
            st.caption(f"📍 Current location: {loc['lat']:.4f}, {loc['lng']:.4f}")

        # Render MapKit JS
        mapkit_html = create_mapkit_html()
        st.components.v1.html(mapkit_html, height=800, scrolling=False)

        # Manual location input as fallback
        with st.expander("📍 Set Location Manually"):
            col_lat, col_lng = st.columns(2)
            with col_lat:
                manual_lat = st.number_input("Latitude", value=37.7749, format="%.6f", key="manual_lat")
            with col_lng:
                manual_lng = st.number_input("Longitude", value=-122.4194, format="%.6f", key="manual_lng")
            if st.button("Update Location", key="update_location"):
                st.session_state.user_preferences['location'] = {
                    'lat': manual_lat,
                    'lng': manual_lng
                }
                st.success(f"Location updated to {manual_lat:.4f}, {manual_lng:.4f}")
                st.rerun()

    # Right column - Chat interface
    with col2:
        st.subheader("Chat")

        # Display chat messages first (before processing new input)
        chat_container = st.container(height=700)
        with chat_container:
            # Display chat history
            for message in st.session_state.messages:
                display_chat_message(message)

        # Chat input (at the bottom)
        prompt = st.chat_input("What kind of restaurant are you looking for?")

    # Process chat input
    if prompt:
        # Add user message to history
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)

        # Build context with preferences
        prefs = st.session_state.user_preferences
        context_parts = []

        if prefs['location']:
            context_parts.append(f"Current location: latitude {prefs['location']['lat']}, longitude {prefs['location']['lng']}")
        if prefs['cuisine']:
            context_parts.append(f"Preferred cuisine: {prefs['cuisine']}")
        if prefs['price_range']:
            context_parts.append(f"Price range: {prefs['price_range']}")
        if prefs['dietary_restrictions']:
            context_parts.append(f"Dietary restrictions: {', '.join(prefs['dietary_restrictions'])}")

        context = "\n".join(context_parts) if context_parts else ""
        full_prompt = f"{context}\n\nUser request: {prompt}" if context else prompt

        # Display user message immediately in the chat
        with chat_container:
            display_chat_message(user_message)

        # Get agent response
        try:
            import asyncio

            # Use async_stream_query for deployed ADK agents
            async def get_response():
                last_recommendation_response = None
                full_trace = []

                async for event in st.session_state.agent.async_stream_query(
                    user_id="streamlit_user",
                    message=full_prompt
                ):
                    # Store full trace for debugging
                    full_trace.append(str(event))

                    # Check if this is the final recommendation agent response
                    if isinstance(event, dict):
                        # Check for RestaurantRecommendationAgent
                        if event.get('author') == 'RestaurantRecommendationAgent':
                            content = event.get('content', {})
                            parts = content.get('parts', [])
                            for part in parts:
                                if 'text' in part:
                                    # This is likely the final JSON response
                                    last_recommendation_response = part['text']

                # Return the final recommendation or the full trace
                if last_recommendation_response:
                    return last_recommendation_response
                else:
                    # Fallback to full trace
                    return "\n".join(full_trace) if full_trace else "No response"

            # Run async function in event loop
            with st.spinner("Searching for restaurants..."):
                response_text = asyncio.run(get_response())

            # Try to extract restaurant coordinates and add to map
            restaurants = extract_restaurants_from_response(response_text)
            if restaurants:
                # Store restaurants in session state for map updates
                st.session_state.current_restaurants = restaurants
                # Format response for better user experience
                formatted_response = format_user_friendly_response(response_text, restaurants)
            else:
                formatted_response = response_text

            # Add assistant message to history (using formatted response)
            assistant_message = {"role": "assistant", "content": formatted_response}
            st.session_state.messages.append(assistant_message)

            # Rerun to display new messages and update map
            st.rerun()

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            assistant_message = {"role": "assistant", "content": error_msg}
            st.session_state.messages.append(assistant_message)
            st.rerun()

    # Update map with current restaurants only if they've changed
    if st.session_state.current_restaurants:
        # Check if restaurants have changed since last map update
        current_hash = json.dumps(st.session_state.current_restaurants, sort_keys=True)
        last_hash = json.dumps(st.session_state.last_sent_restaurants, sort_keys=True) if st.session_state.last_sent_restaurants else None

        if current_hash != last_hash:
            send_markers_to_map(st.session_state.current_restaurants)
            st.session_state.last_sent_restaurants = st.session_state.current_restaurants

if __name__ == "__main__":
    main()
