import { useState } from 'react';
import { StyleSheet, View, TouchableOpacity } from 'react-native';
import { Text, Card, useTheme, Chip } from 'react-native-paper';

export default function ChatMessage({
    message,
    onRestaurantClick,
    selectedRestaurant,
    startingIndex = 0,
}) {
    const theme = useTheme();
    const isUser = message.role === 'user';
    const restaurants = message.restaurants || [];
    const [expandedReviews, setExpandedReviews] = useState({});

    const toggleExpandReviews = (restaurantIndex) => {
        setExpandedReviews(prev => ({
            ...prev,
            [restaurantIndex]: !prev[restaurantIndex]
        }));
    };

    const isRestaurantSelected = (restaurant) => {
        if (!selectedRestaurant) return false;
        return (
            restaurant.name === selectedRestaurant.name &&
            restaurant.latitude === selectedRestaurant.latitude &&
            restaurant.longitude === selectedRestaurant.longitude
        );
    };

    return (
        <View
            style={[
                styles.messageContainer,
                isUser && styles.userMessageContainer,
            ]}
        >
            {/* Summary text message */}
            <Card
                style={[
                    styles.messageCard,
                    isUser
                        ? { backgroundColor: theme.colors.primary }
                        : { backgroundColor: theme.colors.surface },
                ]}
                elevation={1}
            >
                <Card.Content>
                    <Text
                        variant="bodyMedium"
                        style={[
                            styles.messageText,
                            isUser && { color: '#FFFFFF' },
                        ]}
                    >
                        {message.content}
                    </Text>
                </Card.Content>
            </Card>

            {/* Display restaurant cards below if available */}
            {!isUser && restaurants && restaurants.length > 0 && (
                <View style={styles.restaurantsContainer}>
                    <Text variant="titleMedium" style={styles.restaurantsTitle}>
                        Found {restaurants.length} restaurant
                        {restaurants.length !== 1 ? 's' : ''}:
                    </Text>

                    {restaurants.map((restaurant, index) => (
                        <Card
                            key={index}
                            style={[
                                styles.restaurantCard,
                                isRestaurantSelected(restaurant) &&
                                    styles.selectedRestaurantCard,
                            ]}
                            onPress={() =>
                                onRestaurantClick &&
                                onRestaurantClick(restaurant)
                            }
                        >
                            <Card.Content>
                                <Text
                                    variant="titleMedium"
                                    style={styles.restaurantName}
                                >
                                    {startingIndex + index + 1}.{' '}
                                    {restaurant.name}
                                </Text>

                                <View style={styles.restaurantInfo}>
                                    {restaurant.rating && (
                                        <Chip
                                            icon="star"
                                            compact
                                            style={styles.chip}
                                        >
                                            {restaurant.rating}/10
                                        </Chip>
                                    )}
                                    {restaurant.price_level && (
                                        <Chip
                                            icon="currency-usd"
                                            compact
                                            style={styles.chip}
                                        >
                                            {restaurant.price_level}
                                        </Chip>
                                    )}
                                    {restaurant.cuisine_type && (
                                        <Chip
                                            icon="silverware-fork-knife"
                                            compact
                                            style={styles.chip}
                                        >
                                            {restaurant.cuisine_type}
                                        </Chip>
                                    )}
                                    {restaurant.distance_miles && (
                                        <Chip
                                            icon="map-marker-distance"
                                            compact
                                            style={styles.chip}
                                        >
                                            {restaurant.distance_miles.toFixed(
                                                1
                                            )}{' '}
                                            mi
                                        </Chip>
                                    )}
                                </View>

                                {restaurant.address && (
                                    <Text
                                        variant="bodySmall"
                                        style={styles.restaurantAddress}
                                    >
                                        📍 {restaurant.address}
                                    </Text>
                                )}

                                {restaurant.description && (
                                    <Text
                                        variant="bodySmall"
                                        style={styles.restaurantDescription}
                                    >
                                        {restaurant.description}
                                    </Text>
                                )}

                                {/* Reviews Section */}
                                {restaurant.reviews &&
                                    restaurant.reviews.length > 0 && (
                                        <View style={styles.reviewsContainer}>
                                            <Text
                                                variant="labelMedium"
                                                style={styles.reviewsTitle}
                                            >
                                                Reviews
                                            </Text>
                                            {restaurant.reviews.map(
                                                (review, reviewIndex) => {
                                                    const isExpanded = expandedReviews[index];
                                                    const shouldTruncate = review.text.length > 150 && !isExpanded;
                                                    return (
                                                    <View
                                                        key={reviewIndex}
                                                        style={
                                                            styles.reviewItem
                                                        }
                                                    >
                                                        <Text
                                                            variant="labelSmall"
                                                            style={
                                                                styles.reviewAuthor
                                                            }
                                                        >
                                                            {review.author}
                                                        </Text>
                                                        {review.rating && (
                                                            <Text
                                                                variant="labelSmall"
                                                                style={
                                                                    styles.reviewRating
                                                                }
                                                            >
                                                                {'★'.repeat(
                                                                    Math.round(
                                                                        review.rating
                                                                    )
                                                                )}
                                                                {'☆'.repeat(
                                                                    5 -
                                                                        Math.round(
                                                                            review.rating
                                                                        )
                                                                )}
                                                            </Text>
                                                        )}
                                                        <Text
                                                            variant="bodySmall"
                                                            style={
                                                                styles.reviewText
                                                            }
                                                        >
                                                            {shouldTruncate
                                                                ? `${review.text.substring(0, 150)}...`
                                                                : review.text}
                                                        </Text>
                                                    </View>
                                                    );
                                                }
                                            )}
                                            {restaurant.reviews.some(r => r.text.length > 150) && (
                                                <TouchableOpacity
                                                    onPress={(e) => {
                                                        e.stopPropagation();
                                                        toggleExpandReviews(index);
                                                    }}
                                                    style={styles.expandButton}
                                                >
                                                    <Text style={styles.expandButtonText}>
                                                        {expandedReviews[index] ? 'Show Less' : 'Show Full Reviews'}
                                                    </Text>
                                                </TouchableOpacity>
                                            )}
                                        </View>
                                    )}
                            </Card.Content>
                        </Card>
                    ))}
                </View>
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    messageContainer: {
        marginBottom: 16,
        paddingHorizontal: 8,
        alignItems: 'flex-start',
        width: '100%',
    },
    userMessageContainer: {
        alignItems: 'flex-end',
    },
    messageCard: {
        maxWidth: '80%',
        borderRadius: 12,
    },
    messageText: {
        lineHeight: 20,
    },
    restaurantsContainer: {
        marginTop: 16,
        width: '100%',
    },
    restaurantsTitle: {
        fontWeight: '600',
        marginBottom: 12,
        fontSize: 16,
    },
    restaurantCard: {
        marginTop: 12,
        borderRadius: 12,
        backgroundColor: '#FFFFFF',
        borderWidth: 1,
        borderColor: '#E6E9EF',
        cursor: 'pointer',
    },
    selectedRestaurantCard: {
        borderColor: '#FF4B4B',
        borderWidth: 2,
        backgroundColor: '#FFF5F5',
    },
    restaurantName: {
        fontWeight: '600',
        marginBottom: 8,
    },
    restaurantInfo: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 6,
        marginBottom: 8,
    },
    chip: {
        height: 28,
    },
    restaurantAddress: {
        color: '#5F6368',
        marginTop: 4,
    },
    restaurantDescription: {
        color: '#5F6368',
        marginTop: 8,
        fontStyle: 'italic',
    },
    reviewsContainer: {
        marginTop: 12,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: '#E6E9EF',
    },
    reviewsTitle: {
        fontWeight: '600',
        color: '#262730',
        marginBottom: 8,
    },
    reviewItem: {
        marginBottom: 10,
        paddingBottom: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#F0F2F6',
    },
    reviewAuthor: {
        fontWeight: '500',
        color: '#31333F',
        fontSize: 14,
    },
    reviewRating: {
        color: '#FFA000',
        marginBottom: 4,
        fontSize: 16,
    },
    reviewText: {
        color: '#5F6368',
        lineHeight: 18,
    },
    expandButton: {
        marginTop: 8,
        paddingVertical: 8,
        paddingHorizontal: 12,
        backgroundColor: '#E8F0FE',
        borderRadius: 6,
        alignSelf: 'flex-start',
        zIndex: 10,
        elevation: 5,
    },
    expandButtonText: {
        color: '#1A73E8',
        fontSize: 13,
        fontWeight: '500',
    },
});
