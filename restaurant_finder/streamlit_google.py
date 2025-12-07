"""Streamlit chat interface for Restaurant Finder Agent with Google Maps."""

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
    streamlit run streamlit_google.py
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
                        'phone': restaurant.get('phone', ''),
                        'website': restaurant.get('website', ''),
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
        Formatted response text for display with summary and restaurant list
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

        # Build response with summary and restaurant list
        response_parts = []

        if summary:
            response_parts.append(f"{summary}")

        if additional_notes:
            response_parts.append(f"\n**Tips:** {additional_notes}")

        # Add formatted restaurant list
        response_parts.append(f"\n---\n### Restaurants ({len(restaurants)})\n")

        for i, restaurant in enumerate(restaurants, 1):
            restaurant_info = [f"**{i}. {restaurant['name']}**"]

            if restaurant.get('rating'):
                restaurant_info.append(f"⭐ **{restaurant['rating']}** / 10.0")

            if restaurant.get('price_level'):
                restaurant_info.append(f"💰 {restaurant['price_level']}")

            if restaurant.get('cuisine_type'):
                restaurant_info.append(f"🍽️ {restaurant['cuisine_type']}")

            if restaurant.get('distance_miles'):
                restaurant_info.append(f"📍 {restaurant['distance_miles']:.1f} miles")

            if restaurant.get('address'):
                restaurant_info.append(f"📫 {restaurant['address']}")

            if restaurant.get('phone'):
                restaurant_info.append(f"📞 {restaurant['phone']}")

            if restaurant.get('website'):
                restaurant_info.append(f"🌐 [Website]({restaurant['website']})")

            if restaurant.get('description'):
                restaurant_info.append(f"_{restaurant['description']}_")

            response_parts.append("  \n".join(restaurant_info))
            response_parts.append("")  # Add spacing between restaurants

        # Add note about map markers
        response_parts.append(f"\n*Click the markers on the map to see restaurant locations.*")

        return '\n'.join(response_parts)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error formatting response: {e}")
        print(f"Response text (first 500 chars): {response_text[:500]}")

    # Fallback - just show count and instruction
    return f"*Found {len(restaurants)} restaurant(s). Click the markers on the map to see details.*"

def send_markers_to_map(restaurants: List[Dict]):
    """Send restaurant markers to the Google Maps iframe.

    Args:
        restaurants: List of restaurant dictionaries with coordinates
    """
    if not restaurants:
        return

    # Create JavaScript to send markers to the map iframe
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
                        }, index * 100 + 200);
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
            setTimeout(function() {
                sendMarkersToIframe(10);
            }, 1000);
        })();
    </script>
    """

    # Inject the JavaScript
    st.components.v1.html(markers_js, height=0)

def create_google_maps_html():
    """Create HTML for Google Maps JavaScript API integration."""
    # Get Google Maps API key
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

    if not google_maps_api_key:
        return "<div style='padding: 20px; color: red;'>Error: Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in your .env file.</div>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
            let map;
            let userLocationMarker;
            let restaurantMarkers = [];
            let infoWindows = [];

            function initMap() {{
                console.log('Google Maps: Initializing map');

                // Create map centered on San Francisco
                map = new google.maps.Map(document.getElementById('map'), {{
                    center: {{ lat: 37.7749, lng: -122.4194 }},
                    zoom: 12,
                    mapTypeControl: true,
                    streetViewControl: true,
                    fullscreenControl: true
                }});

                // Get user location on load
                getUserLocation();

                // Listen for messages from parent window
                window.addEventListener('message', function(event) {{
                    console.log('Google Maps: Received message', event.data.type);

                    if (event.data.type === 'addRestaurantMarker') {{
                        addRestaurantMarker(event.data.restaurant);
                    }}

                    if (event.data.type === 'clearRestaurantMarkers') {{
                        clearRestaurantMarkers();
                    }}

                    if (event.data.type === 'fitToShowRestaurants') {{
                        fitToShowRestaurants(event.data.restaurants);
                    }}
                }});

                console.log('Google Maps: Map initialized');
            }}

            function getUserLocation() {{
                if (!navigator.geolocation) {{
                    console.error('Geolocation not supported');
                    return;
                }}

                document.getElementById('location-button').textContent = '⌛';

                navigator.geolocation.getCurrentPosition(
                    function(position) {{
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        const userLocation = {{ lat: lat, lng: lng }};

                        // Center map on user location
                        map.setCenter(userLocation);
                        map.setZoom(13);

                        // Remove existing user location marker
                        if (userLocationMarker) {{
                            userLocationMarker.setMap(null);
                        }}

                        // Add blue marker for user location
                        userLocationMarker = new google.maps.Marker({{
                            position: userLocation,
                            map: map,
                            title: 'Your Location',
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 10,
                                fillColor: '#4285F4',
                                fillOpacity: 1,
                                strokeColor: 'white',
                                strokeWeight: 2
                            }}
                        }});

                        // Store location in sessionStorage
                        try {{
                            window.parent.sessionStorage.setItem('userLocation', JSON.stringify({{
                                lat: lat,
                                lng: lng,
                                timestamp: Date.now()
                            }}));
                        }} catch(e) {{
                            console.log('Could not store location:', e);
                        }}

                        document.getElementById('location-button').textContent = '📍';
                        console.log('Google Maps: User location set to', lat, lng);
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

            function addRestaurantMarker(restaurant) {{
                console.log('Google Maps: Adding marker for', restaurant.name);

                const position = {{
                    lat: restaurant.latitude,
                    lng: restaurant.longitude
                }};

                // Create marker
                const marker = new google.maps.Marker({{
                    position: position,
                    map: map,
                    title: restaurant.name,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        scale: 8,
                        fillColor: '#EA4335',
                        fillOpacity: 1,
                        strokeColor: 'white',
                        strokeWeight: 2
                    }}
                }});

                // Create info window content
                let contentHTML = '<div style="padding: 10px; max-width: 300px; font-family: Arial, sans-serif;">';
                contentHTML += '<h3 style="margin: 0 0 10px 0; color: #202124;">' + restaurant.name + '</h3>';

                if (restaurant.rating) {{
                    contentHTML += '<div style="margin: 5px 0; font-size: 14px;">⭐ <b>' + restaurant.rating + '</b> / 10.0</div>';
                }}

                if (restaurant.price_level) {{
                    contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Price Range:</b> ' + restaurant.price_level + '</div>';
                }}

                if (restaurant.cuisine_type) {{
                    contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Cuisine:</b> ' + restaurant.cuisine_type + '</div>';
                }}

                if (restaurant.distance_miles) {{
                    contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Distance:</b> ' + restaurant.distance_miles.toFixed(1) + ' miles</div>';
                }}

                if (restaurant.website) {{
                    contentHTML += '<div style="margin: 8px 0;"><a href="' + restaurant.website + '" target="_blank" style="color: #1a73e8; text-decoration: none; font-size: 14px;">🌐 Visit Website</a></div>';
                }}

                if (restaurant.phone) {{
                    contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Phone:</b> ' + restaurant.phone + '</div>';
                }}

                if (restaurant.address) {{
                    contentHTML += '<div style="margin: 10px 0 5px 0; color: #5f6368; font-size: 13px;"><b>Address:</b><br>' + restaurant.address + '</div>';
                }}

                if (restaurant.description) {{
                    contentHTML += '<div style="margin: 10px 0 0 0; color: #5f6368; font-size: 13px; line-height: 1.4;">' + restaurant.description + '</div>';
                }}

                contentHTML += '</div>';

                const infoWindow = new google.maps.InfoWindow({{
                    content: contentHTML
                }});

                // Open info window on marker click
                marker.addListener('click', function() {{
                    // Close all other info windows
                    infoWindows.forEach(iw => iw.close());
                    infoWindow.open(map, marker);
                }});

                restaurantMarkers.push(marker);
                infoWindows.push(infoWindow);
            }}

            function clearRestaurantMarkers() {{
                console.log('Google Maps: Clearing restaurant markers');
                restaurantMarkers.forEach(marker => marker.setMap(null));
                restaurantMarkers = [];
                infoWindows.forEach(iw => iw.close());
                infoWindows = [];
            }}

            function fitToShowRestaurants(restaurants) {{
                if (!restaurants || restaurants.length === 0) return;

                console.log('Google Maps: Fitting bounds to show', restaurants.length, 'restaurants');

                const bounds = new google.maps.LatLngBounds();

                // Include all restaurant markers
                restaurants.forEach(restaurant => {{
                    bounds.extend({{
                        lat: restaurant.latitude,
                        lng: restaurant.longitude
                    }});
                }});

                // Include user location if available
                if (userLocationMarker) {{
                    bounds.extend(userLocationMarker.getPosition());
                }}

                map.fitBounds(bounds);

                // Add padding
                const padding = {{ top: 50, right: 50, bottom: 50, left: 50 }};
                map.fitBounds(bounds, padding);
            }}

            // Event listener for location button
            document.getElementById('location-button').addEventListener('click', getUserLocation);
        </script>

        <script async defer
            src="https://maps.googleapis.com/maps/api/js?key={google_maps_api_key}&callback=initMap">
        </script>
    </body>
    </html>
    """
    return html_content

def main():
    st.set_page_config(
        page_title="Restaurant Finder Chat (Google Maps)",
        page_icon="🍽️",
        layout="wide"
    )

    st.title("🍽️ Restaurant Finder AI Assistant (Google Maps)")

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
            "with Google Maps integration for real-time restaurant data."
        )

    # Split main screen into two columns
    col1, col2 = st.columns(2)

    # Left column - Google Maps
    with col1:
        st.subheader("Map")

        # Display current location if available
        if st.session_state.user_preferences['location']:
            loc = st.session_state.user_preferences['location']
            st.caption(f"📍 Current location: {loc['lat']:.4f}, {loc['lng']:.4f}")

        # Render Google Maps
        google_maps_html = create_google_maps_html()
        st.components.v1.html(google_maps_html, height=800, scrolling=False)

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
