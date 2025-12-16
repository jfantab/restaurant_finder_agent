import React, { useEffect, useRef, memo } from 'react';
import { StyleSheet, View, Platform } from 'react-native';
import { Text, IconButton, useTheme } from 'react-native-paper';
import config from '../../config';

function GoogleMap({ restaurants, userLocation, onLocationChange, selectedRestaurant }) {
  const mapContainerRef = useRef(null);
  const iframeRef = useRef(null);
  const theme = useTheme();

  useEffect(() => {
    if (Platform.OS === 'web' && mapContainerRef.current) {
      // Create iframe with Google Maps
      const mapHtml = createMapHTML(restaurants, userLocation);
      const iframe = document.createElement('iframe');
      iframe.style.width = '100%';
      iframe.style.height = '600px';
      iframe.style.border = 'none';
      iframe.style.borderRadius = '8px';
      iframe.srcdoc = mapHtml;

      mapContainerRef.current.innerHTML = '';
      mapContainerRef.current.appendChild(iframe);
      iframeRef.current = iframe;
    }
  }, [restaurants, userLocation]);

  // Handle selected restaurant changes
  useEffect(() => {
    if (Platform.OS === 'web' && iframeRef.current && selectedRestaurant) {
      // Small delay to ensure iframe map is fully initialized
      const timer = setTimeout(() => {
        console.log('Sending SELECT_RESTAURANT:', selectedRestaurant.name, selectedRestaurant.latitude, selectedRestaurant.longitude);
        iframeRef.current?.contentWindow?.postMessage({
          type: 'SELECT_RESTAURANT',
          restaurant: selectedRestaurant
        }, '*');
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [selectedRestaurant]);

  const createMapHTML = (restaurants, userLocation) => {
    const center = userLocation || { lat: 37.7749, lng: -122.4194 };
    const restaurantsJSON = JSON.stringify(restaurants || []);

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body { margin: 0; padding: 0; height: 100vh; overflow: hidden; }
          #map { width: 100%; height: 100%; }
          #location-button {
            position: absolute; top: 10px; right: 10px; z-index: 1000;
            background: white; border: none; border-radius: 8px;
            padding: 10px 15px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
            cursor: pointer; font-size: 20px; transition: background-color 0.2s;
          }
          #location-button:hover { background-color: #f0f0f0; }
        </style>
      </head>
      <body>
        <button id="location-button" title="Get Current Location">📍</button>
        <div id="map"></div>

        <script>
          let map, userMarker, restaurantMarkers = [], infoWindows = [];
          let mapReady = false;
          let pendingSelection = null;

          function selectRestaurant(selectedRestaurant) {
            console.log('selectRestaurant called:', selectedRestaurant.name, 'lat:', selectedRestaurant.latitude, 'lng:', selectedRestaurant.longitude);

            // Make sure map is initialized
            if (!mapReady || !map || restaurantMarkers.length === 0) {
              console.log('Map not ready yet - mapReady:', mapReady, 'markers:', restaurantMarkers.length);
              pendingSelection = selectedRestaurant;
              return;
            }

            console.log('Searching through', restaurantMarkers.length, 'markers');

            // Find the matching marker by comparing with marker positions
            let foundMarker = null;
            let foundInfoWindow = null;

            for (let i = 0; i < restaurantMarkers.length; i++) {
              const marker = restaurantMarkers[i];
              const pos = marker.getPosition();
              const markerLat = pos ? pos.lat() : null;
              const markerLng = pos ? pos.lng() : null;

              if (pos &&
                  Math.abs(markerLat - selectedRestaurant.latitude) < 0.0001 &&
                  Math.abs(markerLng - selectedRestaurant.longitude) < 0.0001) {
                foundMarker = marker;
                foundInfoWindow = infoWindows[i];
                console.log('Found matching marker at index', i);
                break;
              }
            }

            if (foundMarker) {
              // Close all info windows
              infoWindows.forEach(iw => iw.close());

              // Open the selected restaurant's info window
              foundInfoWindow.open(map, foundMarker);

              // Center map on the selected marker with a zoom
              map.setCenter(foundMarker.getPosition());
              map.setZoom(15);

              // Highlight the marker by scaling up the icon temporarily
              // (BOUNCE animation causes the label to disappear with custom SVG icons)
              const originalIcon = foundMarker.getIcon();
              const highlightedIcon = {
                ...originalIcon,
                scale: 2.0,
                fillColor: '#C62828'
              };
              foundMarker.setIcon(highlightedIcon);
              setTimeout(() => foundMarker.setIcon(originalIcon), 1500);
            } else {
              console.log('No marker found for:', selectedRestaurant.name, 'looking for lat:', selectedRestaurant.latitude, 'lng:', selectedRestaurant.longitude);
              // Log all marker positions for debugging
              restaurantMarkers.forEach((m, idx) => {
                const p = m.getPosition();
                console.log('Marker', idx, ':', m.getTitle(), 'lat:', p?.lat(), 'lng:', p?.lng());
              });
            }
          }

          // Listen for messages from parent window to select restaurant
          window.addEventListener('message', (event) => {
            if (event.data.type === 'SELECT_RESTAURANT' && event.data.restaurant) {
              selectRestaurant(event.data.restaurant);
            }
          });

          function initMap() {
            map = new google.maps.Map(document.getElementById('map'), {
              center: { lat: ${center.lat}, lng: ${center.lng} },
              zoom: 12,
              mapTypeControl: true,
              streetViewControl: true,
              fullscreenControl: true
            });

            // Add user location marker
            if (${userLocation !== null}) {
              userMarker = new google.maps.Marker({
                position: { lat: ${center.lat}, lng: ${center.lng} },
                map: map,
                title: 'Your Location',
                icon: {
                  path: google.maps.SymbolPath.CIRCLE,
                  scale: 10,
                  fillColor: '#4285F4',
                  fillOpacity: 1,
                  strokeColor: 'white',
                  strokeWeight: 2
                }
              });
            }

            // Add restaurant markers
            const restaurants = ${restaurantsJSON};
            restaurants.forEach((restaurant, index) => {
              const markerNumber = index + 1;
              const marker = new google.maps.Marker({
                position: { lat: restaurant.latitude, lng: restaurant.longitude },
                map: map,
                title: restaurant.name,
                label: {
                  text: String(markerNumber),
                  color: 'white',
                  fontSize: '12px',
                  fontWeight: 'bold'
                },
                icon: {
                  path: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z',
                  fillColor: '#EA4335',
                  fillOpacity: 1,
                  strokeColor: 'white',
                  strokeWeight: 2,
                  scale: 1.5,
                  anchor: new google.maps.Point(12, 22),
                  labelOrigin: new google.maps.Point(12, 10)
                }
              });

              let contentHTML = '<div style="padding: 10px; max-width: 300px; font-family: Arial, sans-serif;">';
              contentHTML += '<h3 style="margin: 0 0 10px 0; color: #202124;">' + restaurant.name + '</h3>';

              if (restaurant.rating) {
                contentHTML += '<div style="margin: 5px 0; font-size: 14px;">⭐ <b>' + restaurant.rating + '</b> / 10.0</div>';
              }

              if (restaurant.price_level) {
                contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Price:</b> ' + restaurant.price_level + '</div>';
              }

              if (restaurant.cuisine_type) {
                contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Cuisine:</b> ' + restaurant.cuisine_type + '</div>';
              }

              if (restaurant.distance_miles) {
                contentHTML += '<div style="margin: 5px 0; color: #5f6368; font-size: 14px;"><b>Distance:</b> ' + restaurant.distance_miles.toFixed(1) + ' miles</div>';
              }

              if (restaurant.address) {
                contentHTML += '<div style="margin: 10px 0 5px 0; color: #5f6368; font-size: 13px;"><b>Address:</b><br>' + restaurant.address + '</div>';
              }

              contentHTML += '</div>';

              const infoWindow = new google.maps.InfoWindow({ content: contentHTML });

              marker.addListener('click', () => {
                infoWindows.forEach(iw => iw.close());
                infoWindow.open(map, marker);
              });

              restaurantMarkers.push(marker);
              infoWindows.push(infoWindow);
            });

            // Fit bounds to show all markers
            if (restaurants.length > 0) {
              const bounds = new google.maps.LatLngBounds();
              restaurants.forEach(r => bounds.extend({ lat: r.latitude, lng: r.longitude }));
              if (userMarker) bounds.extend(userMarker.getPosition());

              // Fit bounds with padding for better visibility
              map.fitBounds(bounds, {
                padding: { top: 80, right: 80, bottom: 80, left: 80 }
              });

              // Set a zoom level after a short delay to ensure bounds are set
              setTimeout(() => {
                const currentZoom = map.getZoom();
                // Constrain zoom to a reasonable range
                if (currentZoom > 14) {
                  map.setZoom(14);
                } else if (currentZoom < 12) {
                  map.setZoom(12);
                }
              }, 100);
            }

            document.getElementById('location-button').addEventListener('click', () => {
              if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(position => {
                  const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
                  map.setCenter(pos);
                  map.setZoom(13);

                  if (userMarker) userMarker.setMap(null);

                  userMarker = new google.maps.Marker({
                    position: pos,
                    map: map,
                    title: 'Your Location',
                    icon: {
                      path: google.maps.SymbolPath.CIRCLE,
                      scale: 10,
                      fillColor: '#4285F4',
                      fillOpacity: 1,
                      strokeColor: 'white',
                      strokeWeight: 2
                    }
                  });
                });
              }
            });

            // Mark map as ready and process any pending selection
            mapReady = true;
            console.log('Map initialized with', restaurantMarkers.length, 'markers');
            if (pendingSelection) {
              console.log('Processing pending selection:', pendingSelection.name);
              selectRestaurant(pendingSelection);
              pendingSelection = null;
            }
          }
        </script>

        <script async defer
          src="https://maps.googleapis.com/maps/api/js?key=${config.GOOGLE_MAPS_API_KEY}&callback=initMap">
        </script>
      </body>
      </html>
    `;
  };

  if (Platform.OS !== 'web') {
    return (
      <View style={styles.container}>
        <Text>Map view is only available on web</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    minHeight: 600,
    borderRadius: 8,
    overflow: 'hidden',
  },
});

// Custom comparison to prevent unnecessary re-renders
function arePropsEqual(prevProps, nextProps) {
  // Compare restaurants by length and content (not reference)
  const prevRestaurants = prevProps.restaurants || [];
  const nextRestaurants = nextProps.restaurants || [];

  if (prevRestaurants.length !== nextRestaurants.length) {
    return false;
  }

  // Check if restaurant data actually changed
  for (let i = 0; i < prevRestaurants.length; i++) {
    if (prevRestaurants[i].latitude !== nextRestaurants[i].latitude ||
        prevRestaurants[i].longitude !== nextRestaurants[i].longitude ||
        prevRestaurants[i].name !== nextRestaurants[i].name) {
      return false;
    }
  }

  // Compare userLocation
  const prevLoc = prevProps.userLocation;
  const nextLoc = nextProps.userLocation;
  if (prevLoc?.lat !== nextLoc?.lat || prevLoc?.lng !== nextLoc?.lng) {
    return false;
  }

  // Compare selectedRestaurant
  const prevSelected = prevProps.selectedRestaurant;
  const nextSelected = nextProps.selectedRestaurant;
  if (prevSelected?.latitude !== nextSelected?.latitude ||
      prevSelected?.longitude !== nextSelected?.longitude) {
    return false;
  }

  return true;
}

export default memo(GoogleMap, arePropsEqual);
