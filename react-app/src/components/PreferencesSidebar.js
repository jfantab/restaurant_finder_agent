import React, { useState, useEffect } from 'react';
import { StyleSheet, View, ScrollView } from 'react-native';
import { Text, List, Divider, useTheme, Menu, Button, IconButton, Switch } from 'react-native-paper';
import Slider from '@react-native-community/slider';
import STButton from './STButton';

export default function PreferencesSidebar({ preferences, onPreferencesChange, userLocation, onLocationChange, onClose }) {
  const theme = useTheme();
  const [cuisineMenuVisible, setCuisineMenuVisible] = useState(false);
  const [dietaryMenuVisible, setDietaryMenuVisible] = useState(false);
  const [cityName, setCityName] = useState('');

  // Reverse geocode to get city name from coordinates
  useEffect(() => {
    if (userLocation?.lat && userLocation?.lng) {
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${userLocation.lat}&lon=${userLocation.lng}`)
        .then(response => response.json())
        .then(data => {
          const city = data.address?.city || data.address?.town || data.address?.village || data.address?.municipality || data.address?.county || '';
          const state = data.address?.state || '';
          if (city && state) {
            setCityName(`${city}, ${state}`);
          } else if (city) {
            setCityName(city);
          } else if (state) {
            setCityName(state);
          } else {
            setCityName('Unknown location');
          }
        })
        .catch(error => {
          console.error('Error reverse geocoding:', error);
          setCityName('Location unavailable');
        });
    }
  }, [userLocation?.lat, userLocation?.lng]);

  const cuisineOptions = [
    'Italian', 'Japanese', 'Mexican', 'Chinese', 'French',
    'Indian', 'American', 'Mediterranean', 'Thai', 'Korean'
  ];

  const priceOptions = ['$', '$$', '$$$', '$$$$'];

  const dietaryOptions = ['Vegetarian', 'Vegan', 'Gluten-Free', 'Halal', 'Kosher'];

  const handleCuisineChange = (cuisine) => {
    onPreferencesChange({
      ...preferences,
      cuisine: cuisine,
    });
    setCuisineMenuVisible(false);
  };

  const handlePriceChange = (price) => {
    onPreferencesChange({
      ...preferences,
      price_range: preferences.price_range === price ? '' : price,
    });
  };

  const handleDietaryToggle = (dietary) => {
    const newRestrictions = preferences.dietary_restrictions.includes(dietary)
      ? preferences.dietary_restrictions.filter(d => d !== dietary)
      : [...preferences.dietary_restrictions, dietary];

    onPreferencesChange({
      ...preferences,
      dietary_restrictions: newRestrictions,
    });
  };

  const handleDistanceChange = (value) => {
    onPreferencesChange({
      ...preferences,
      distance: value,
    });
  };

  const getDietaryDisplayText = () => {
    if (preferences.dietary_restrictions.length === 0) {
      return 'Select Dietary Restrictions';
    }
    if (preferences.dietary_restrictions.length === 1) {
      return preferences.dietary_restrictions[0];
    }
    return `${preferences.dietary_restrictions.length} selected`;
  };

  const handleGetCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const newLocation = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };
          onLocationChange(newLocation);
        },
        (error) => {
          console.error('Error getting location:', error);
          alert('Unable to get your location. Please enable location services.');
        }
      );
    }
  };

  return (
    <View style={[styles.sidebar, { backgroundColor: theme.colors.surfaceVariant }]}>
      <View style={styles.sidebarHeader}>
        <Text variant="headlineSmall" style={styles.sidebarTitle}>
          Preferences
        </Text>
        <IconButton
          icon="close"
          size={24}
          onPress={onClose}
        />
      </View>
      <Divider />
      <ScrollView style={styles.sidebarContent}>
        {/* Location */}
        <List.Section>
          <List.Subheader>Location</List.Subheader>
          {cityName && (
            <View style={styles.locationDisplay}>
              <Text variant="bodyLarge" style={styles.cityName}>
                {cityName}
              </Text>
            </View>
          )}
          <STButton
            mode="outlined"
            icon="crosshairs-gps"
            onPress={handleGetCurrentLocation}
            style={styles.button}
          >
            Get Current Location
          </STButton>
        </List.Section>

        <Divider />

        {/* Search Distance */}
        <List.Section>
          <List.Subheader>Search Distance</List.Subheader>
          <View style={styles.sliderContainer}>
            <Slider
              style={styles.slider}
              minimumValue={1}
              maximumValue={25}
              step={1}
              value={preferences.distance || 5}
              onValueChange={handleDistanceChange}
              minimumTrackTintColor={theme.colors.primary}
              maximumTrackTintColor="#E0E0E0"
              thumbTintColor={theme.colors.primary}
            />
            <Text variant="bodyMedium" style={styles.sliderValue}>
              {preferences.distance || 5} miles
            </Text>
          </View>
        </List.Section>

        <Divider />

        {/* Cuisine Type */}
        <List.Section>
          <List.Subheader>Cuisine Type</List.Subheader>
          <View style={styles.dropdownContainer}>
            <Menu
              visible={cuisineMenuVisible}
              onDismiss={() => setCuisineMenuVisible(false)}
              anchor={
                <Button
                  mode="outlined"
                  onPress={() => setCuisineMenuVisible(true)}
                  style={styles.dropdownButton}
                  contentStyle={styles.dropdownButtonContent}
                  icon="chevron-down"
                >
                  {preferences.cuisine || 'Select Cuisine'}
                </Button>
              }
            >
              <Menu.Item onPress={() => handleCuisineChange('')} title="None" />
              <Divider />
              {cuisineOptions.map((cuisine) => (
                <Menu.Item
                  key={cuisine}
                  onPress={() => handleCuisineChange(cuisine)}
                  title={cuisine}
                />
              ))}
            </Menu>
          </View>
        </List.Section>

        <Divider />

        {/* Price Range */}
        <List.Section>
          <List.Subheader>Price Range</List.Subheader>
          <View style={styles.priceContainer}>
            {priceOptions.map((price) => (
              <STButton
                key={price}
                mode={preferences.price_range === price ? 'contained' : 'outlined'}
                onPress={() => handlePriceChange(price)}
                style={styles.priceButton}
                compact
              >
                {price}
              </STButton>
            ))}
          </View>
        </List.Section>

        <Divider />

        {/* Dietary Restrictions */}
        <List.Section>
          <List.Subheader>Dietary Restrictions</List.Subheader>
          <View style={styles.dropdownContainer}>
            <Menu
              visible={dietaryMenuVisible}
              onDismiss={() => setDietaryMenuVisible(false)}
              anchor={
                <Button
                  mode="outlined"
                  onPress={() => setDietaryMenuVisible(true)}
                  style={styles.dropdownButton}
                  contentStyle={styles.dropdownButtonContent}
                  icon="chevron-down"
                >
                  {getDietaryDisplayText()}
                </Button>
              }
            >
              {dietaryOptions.map((dietary) => (
                <Menu.Item
                  key={dietary}
                  onPress={() => handleDietaryToggle(dietary)}
                  title={dietary}
                  leadingIcon={preferences.dietary_restrictions.includes(dietary) ? 'check' : undefined}
                />
              ))}
              {preferences.dietary_restrictions.length > 0 && (
                <>
                  <Divider />
                  <Menu.Item
                    onPress={() => {
                      onPreferencesChange({
                        ...preferences,
                        dietary_restrictions: [],
                      });
                    }}
                    title="Clear All"
                  />
                </>
              )}
            </Menu>
          </View>
        </List.Section>

        <Divider />

        {/* Voice Mode */}
        <List.Section>
          <List.Subheader>Voice Mode</List.Subheader>
          <View style={styles.switchContainer}>
            <View style={styles.switchLabelContainer}>
              <Text variant="bodyMedium" style={styles.switchLabel}>
                Enable Voice Responses
              </Text>
              <Text variant="bodySmall" style={styles.switchDescription}>
                Agent will speak out response summaries
              </Text>
            </View>
            <Switch
              value={preferences.voiceMode || false}
              onValueChange={(value) => {
                onPreferencesChange({
                  ...preferences,
                  voiceMode: value,
                });
              }}
            />
          </View>
        </List.Section>

        <Divider />

        {/* Clear Preferences */}
        <View style={styles.clearContainer}>
          <STButton
            mode="outlined"
            onPress={() => onPreferencesChange({
              cuisine: '',
              price_range: '',
              dietary_restrictions: [],
              distance: 5,
              voiceMode: false,
            })}
            style={styles.button}
          >
            Clear All Preferences
          </STButton>
        </View>

        <View style={styles.aboutContainer}>
          <Text variant="bodySmall" style={styles.aboutText}>
            AI-powered restaurant finder using Google's Agent Development Kit with Google Maps integration.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  sidebar: {
    width: 320,
    borderRightWidth: 1,
    borderRightColor: '#E6E9EF',
  },
  sidebarHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    paddingVertical: 20,
  },
  sidebarTitle: {
    fontWeight: '600',
  },
  sidebarContent: {
    flex: 1,
    padding: 16,
  },
  button: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  locationDisplay: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  cityName: {
    fontWeight: '500',
    color: '#333',
  },
  dropdownContainer: {
    paddingHorizontal: 16,
    marginVertical: 8,
  },
  dropdownButton: {
    width: '100%',
    justifyContent: 'flex-start',
  },
  dropdownButtonContent: {
    flexDirection: 'row-reverse',
    justifyContent: 'space-between',
  },
  sliderContainer: {
    paddingHorizontal: 16,
    marginVertical: 8,
  },
  slider: {
    width: '100%',
    height: 40,
  },
  sliderValue: {
    textAlign: 'center',
    color: '#333',
    fontWeight: '500',
  },
  priceContainer: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 16,
  },
  priceButton: {
    flex: 1,
  },
  switchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  switchLabelContainer: {
    flex: 1,
    marginRight: 16,
  },
  switchLabel: {
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  switchDescription: {
    color: '#666',
    lineHeight: 16,
  },
  clearContainer: {
    paddingVertical: 16,
  },
  aboutContainer: {
    padding: 16,
    paddingTop: 8,
  },
  aboutText: {
    color: '#666',
    lineHeight: 18,
  },
});
