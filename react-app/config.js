// Configuration file for environment variables
import Constants from 'expo-constants';

const config = {
  GOOGLE_MAPS_API_KEY: Constants.expoConfig?.extra?.googleMapsApiKey || process.env.GOOGLE_MAPS_API_KEY || '',
  API_URL: Constants.expoConfig?.extra?.apiUrl || process.env.API_URL || 'http://localhost:8001',
  DEEPGRAM_API_KEY: Constants.expoConfig?.extra?.deepgramApiKey || process.env.DEEPGRAM_API_KEY || '',
};

// Debug logging for web
if (typeof window !== 'undefined') {
  console.log('[Config] Environment loaded:', {
    hasGoogleMapsKey: !!config.GOOGLE_MAPS_API_KEY,
    hasDeepgramKey: !!config.DEEPGRAM_API_KEY,
    apiUrl: config.API_URL,
  });
}

export default config;
