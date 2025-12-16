// Configuration file for environment variables
import Constants from 'expo-constants';

const config = {
  GOOGLE_MAPS_API_KEY: Constants.expoConfig?.extra?.googleMapsApiKey || process.env.GOOGLE_MAPS_API_KEY || '',
  API_URL: Constants.expoConfig?.extra?.apiUrl || process.env.API_URL || 'http://localhost:8001',
};

export default config;
