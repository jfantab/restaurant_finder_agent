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
      deepgramApiKey: process.env.DEEPGRAM_API_KEY,
      firebaseApiKey: process.env.REACT_APP_FIREBASE_API_KEY,
      firebaseAuthDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
      firebaseProjectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
      firebaseStorageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
      firebaseMessagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
      firebaseAppId: process.env.REACT_APP_FIREBASE_APP_ID,
      firebaseMeasurementId: process.env.REACT_APP_FIREBASE_MEASUREMENT_ID,
    },
  },
};
