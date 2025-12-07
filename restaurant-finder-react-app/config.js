// Configuration file for environment variables
// For web builds, these need to be set at build time

const config = {
  GOOGLE_MAPS_API_KEY: process.env.GOOGLE_MAPS_API_KEY || '',
  API_URL: process.env.API_URL || 'http://localhost:8001',
};

export default config;
