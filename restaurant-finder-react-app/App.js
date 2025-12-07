import React from 'react';
import { StyleSheet, View } from 'react-native';
import { Provider as PaperProvider, MD3LightTheme } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import RestaurantFinderPage from './src/pages/RestaurantFinderPage';

// Google Material Design inspired theme with Streamlit aesthetics
const theme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary: '#FF4B4B', // Streamlit red
    secondary: '#0068C9', // Streamlit blue
    tertiary: '#83C9FF', // Light blue
    background: '#FFFFFF',
    surface: '#FAFAFA',
    surfaceVariant: '#F0F2F6',
    onSurface: '#262730',
    onSurfaceVariant: '#31333F',
    outline: '#E6E9EF',
  },
  roundness: 8,
};

export default function App() {
  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <View style={styles.container}>
          <RestaurantFinderPage />
        </View>
      </PaperProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
});
