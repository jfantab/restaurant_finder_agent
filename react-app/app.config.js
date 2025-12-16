import 'dotenv/config';

export default {
  expo: {
    name: "Restaurant Finder React App",
    slug: "restaurant-finder-react-app",
    version: "1.0.0",
    orientation: "portrait",
    userInterfaceStyle: "light",
    assetBundlePatterns: ["**/*"],
    ios: {
      supportsTablet: true,
    },
    android: {},
    web: {
      bundler: "metro",
      name: "Restaurant Finder",
    },
    extra: {
      googleMapsApiKey: process.env.GOOGLE_MAPS_API_KEY,
      apiUrl: process.env.API_URL,
    },
  },
};
