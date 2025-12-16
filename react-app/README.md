# Restaurant Finder AI - Streamlit-Style React Native Web App

A React Native Web application that provides a beautiful, Streamlit-inspired UI for the Restaurant Finder AI agent. This app mimics the clean interface of Streamlit Google with real-time chat, Google Maps integration, and intelligent restaurant recommendations.

## Features

- **Restaurant Finder AI Integration**
  - Real-time chat interface to interact with AI agent
  - Intelligent restaurant search and recommendations
  - Context-aware responses based on preferences
  - Sequential agent workflow (Search → Filter → Recommend)

- **Google Maps Integration**
  - Interactive map with restaurant markers
  - Real-time location tracking
  - Click markers to view restaurant details
  - Auto-fit bounds to show all results

- **Smart Preferences**
  - Cuisine type selection
  - Price range filtering
  - Dietary restrictions (Vegetarian, Vegan, Gluten-Free, Halal, Kosher)
  - Location-based search (GPS or manual)

- **Streamlit-Inspired UI**
  - Clean, minimalist Google Material Design
  - Two-column layout (Map + Chat)
  - Responsive sidebar for preferences
  - Streamlit's signature red (#FF4B4B) theme

## Getting Started

### Prerequisites

- Node.js 14 or higher
- Python 3.9+ (for backend)
- Google Cloud Project with:
  - Vertex AI API enabled
  - Google Maps JavaScript API key
  - Restaurant Finder Agent deployed to Vertex AI

### Installation

#### 1. Backend Setup

Navigate to the backend directory and install Python dependencies:

```bash
cd streamlit-react-app/backend
pip install -r requirements.txt
```

Set up your environment variables (copy from your restaurant_finder project):

```bash
# Copy .env from restaurant_finder or create new one
cp ../../restaurant_finder/.env .env
```

Required environment variables in `.env`:
- `GOOGLE_CLOUD_PROJECT` - Your Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION` - Location (e.g., us-west1)
- `GOOGLE_MAPS_API_KEY` - Your Google Maps API key
- `USE_CLOUD_MCP` - Set to "true" for Cloud Run MCP server

#### 2. Frontend Setup

Navigate to the streamlit-react-app directory:

```bash
cd ..
npm install --legacy-peer-deps
```

### Running the Application

#### 1. Start the Backend Server

```bash
cd backend
python server.py
```

The backend API will start on `http://localhost:5000`

#### 2. Start the Frontend (in a new terminal)

```bash
cd streamlit-react-app
npm run web
```

The app will open in your browser at `http://localhost:8081` (or similar)

### Testing Without Backend

If you want to test the UI without the backend, you can modify the API calls in [RestaurantFinderPage.js](src/pages/RestaurantFinderPage.js:80-115) to return mock data.

## Project Structure

```
streamlit-react-app/
├── App.js                          # Main app component
├── index.js                        # Entry point
├── package.json                    # Frontend dependencies
├── app.json                        # Expo configuration
├── babel.config.js                 # Babel configuration
├── backend/
│   ├── server.py                   # Flask API server
│   └── requirements.txt            # Python dependencies
├── src/
│   ├── components/
│   │   ├── ChatMessage.js          # Chat message display with restaurant cards
│   │   ├── GoogleMap.js            # Google Maps integration
│   │   ├── PreferencesSidebar.js   # Preferences sidebar
│   │   ├── STButton.js             # Streamlit-style button
│   │   ├── STCard.js               # Container card component
│   │   ├── STCheckbox.js           # Checkbox component
│   │   ├── STTextInput.js          # Text input component
│   │   └── ... (other ST components)
│   └── pages/
│       └── RestaurantFinderPage.js # Main restaurant finder interface
└── README.md
```

## How It Works

1. **User Interaction**: User enters a query like "Find me Italian restaurants nearby" and sets preferences (cuisine, price, dietary restrictions)

2. **Frontend Request**: The React app sends the query + preferences + location to the Flask backend at `/api/search`

3. **Agent Processing**: The backend forwards the request to the Vertex AI deployed Restaurant Finder Agent, which:
   - Uses SearchAgent to find restaurants via Google Places API
   - Uses FilterAgent to rank and filter results
   - Uses RecommendationAgent to format final recommendations

4. **Response Display**: The frontend receives restaurant data and displays:
   - Chat message with restaurant details
   - Interactive markers on Google Maps
   - Clickable restaurant cards with ratings, prices, and info

## API Endpoints

### POST `/api/health`
Health check endpoint

### POST `/api/search`
Search for restaurants

**Request Body:**
```json
{
  "query": "Italian restaurants",
  "location": {"lat": 37.7749, "lng": -122.4194},
  "preferences": {
    "cuisine": "Italian",
    "price_range": "$$",
    "dietary_restrictions": ["Vegetarian"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "response": "Full agent response text",
  "restaurants": [
    {
      "name": "Restaurant Name",
      "address": "123 Main St",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "cuisine_type": "Italian",
      "rating": 8.5,
      "price_level": "$$",
      "distance_miles": 1.2,
      "phone": "(555) 123-4567",
      "website": "https://example.com",
      "description": "Great Italian food"
    }
  ]
}
```

## Customization

- **Theme**: Modify the theme in [App.js](App.js:8-23) to customize colors and styling
- **API URL**: Change the API_URL in [RestaurantFinderPage.js](src/pages/RestaurantFinderPage.js:11) to point to your backend
- **Google Maps API Key**: Set in [GoogleMap.js](src/components/GoogleMap.js:6) or via environment variable

## Technologies Used

### Frontend
- **React Native** - Cross-platform mobile framework
- **React Native Web** - Web support for React Native
- **Expo** - Development platform
- **React Native Paper** - Material Design components
- **Google Maps JavaScript API** - Interactive maps

### Backend
- **Flask** - Python web framework
- **Google Cloud Vertex AI** - AI agent platform
- **Google Agent Development Kit (ADK)** - Agent framework
- **Google Places API** - Restaurant data

## Screenshots

The app features:
- **Left Panel**: Interactive Google Maps with restaurant markers
- **Right Panel**: Chat interface with AI agent
- **Sidebar**: Preferences for cuisine, price, location, and dietary restrictions
- **Streamlit-Style Design**: Clean, minimalist Google Material Design aesthetic

## Troubleshooting

### Backend Connection Issues
- Make sure the backend server is running on `http://localhost:5000`
- Check that your `.env` file has all required variables
- Verify your Vertex AI agent is deployed

### Map Not Loading
- Ensure `GOOGLE_MAPS_API_KEY` is set correctly
- Check browser console for API key errors
- Verify Google Maps JavaScript API is enabled in Google Cloud Console

### Agent Not Responding
- Check backend logs for errors
- Verify the Restaurant Finder Agent is deployed in Vertex AI
- Ensure MCP servers are running (if using local MCP)

## License

MIT
