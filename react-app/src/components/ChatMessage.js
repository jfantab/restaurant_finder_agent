import { useState } from 'react';
import { StyleSheet, View, TouchableOpacity, Modal, ScrollView, Linking, Pressable } from 'react-native';
import { Text, Card, useTheme, Chip, IconButton } from 'react-native-paper';

export default function ChatMessage({
    message,
    onRestaurantClick,
    selectedRestaurant,
    startingIndex = 0,
    hideMessageText = false,
}) {
    const theme = useTheme();
    const isUser = message.role === 'user';
    const restaurants = message.restaurants || [];
    const [modalVisible, setModalVisible] = useState(false);
    const [modalRestaurant, setModalRestaurant] = useState(null);

    const isRestaurantSelected = (restaurant) => {
        if (!selectedRestaurant) return false;
        return (
            restaurant.name === selectedRestaurant.name &&
            restaurant.latitude === selectedRestaurant.latitude &&
            restaurant.longitude === selectedRestaurant.longitude
        );
    };

    const openModal = (restaurant, e) => {
        e.stopPropagation();
        setModalRestaurant(restaurant);
        setModalVisible(true);
    };

    const closeModal = () => {
        setModalVisible(false);
        setModalRestaurant(null);
    };

    const openPhone = (phone) => {
        if (phone) {
            Linking.openURL(`tel:${phone}`);
        }
    };

    const openWebsite = (website) => {
        if (website) {
            Linking.openURL(website);
        }
    };

    const openDirections = (restaurant) => {
        if (restaurant.latitude && restaurant.longitude) {
            const url = `https://www.google.com/maps/dir/?api=1&destination=${restaurant.latitude},${restaurant.longitude}`;
            Linking.openURL(url);
        } else if (restaurant.address) {
            const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(restaurant.address)}`;
            Linking.openURL(url);
        }
    };

    return (
        <View
            style={[
                styles.messageContainer,
                isUser && styles.userMessageContainer,
            ]}
        >
            {/* Summary text message */}
            {!hideMessageText && (
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
            )}

            {/* Display restaurant cards below if available */}
            {!isUser && restaurants && restaurants.length > 0 && (
                <View style={styles.restaurantsContainer}>
                    {!hideMessageText && (
                        <Text variant="titleMedium" style={styles.restaurantsTitle}>
                            Found {restaurants.length} restaurant
                            {restaurants.length !== 1 ? 's' : ''}:
                        </Text>
                    )}

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
                                <View style={styles.cardHeader}>
                                    <Text
                                        variant="titleMedium"
                                        style={styles.restaurantName}
                                    >
                                        {startingIndex + index + 1}.{' '}
                                        {restaurant.name}
                                    </Text>
                                    <IconButton
                                        icon="arrow-expand"
                                        size={20}
                                        onPress={(e) => openModal(restaurant, e)}
                                        style={styles.expandIconButton}
                                    />
                                </View>

                                <View style={styles.restaurantInfo}>
                                    {restaurant.rating && (
                                        <Chip
                                            icon="star"
                                            compact
                                            style={styles.chip}
                                        >
                                            {restaurant.rating}/5
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
                                        {restaurant.address}
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

                                {/* Review Summary Section */}
                                {restaurant.review_summary && (
                                    <View style={styles.reviewSummaryContainer}>
                                        <Text
                                            variant="labelMedium"
                                            style={styles.reviewSummaryTitle}
                                        >
                                            Customer Reviews
                                        </Text>
                                        <Text
                                            variant="bodySmall"
                                            style={styles.reviewSummaryText}
                                        >
                                            {restaurant.review_summary}
                                        </Text>
                                    </View>
                                )}
                            </Card.Content>
                        </Card>
                    ))}
                </View>
            )}

            {/* Restaurant Detail Modal */}
            <Modal
                animationType="fade"
                transparent={true}
                visible={modalVisible}
                onRequestClose={closeModal}
            >
                <Pressable style={styles.modalOverlay} onPress={closeModal}>
                    <Pressable style={styles.modalContent} onPress={(e) => e.stopPropagation()}>
                        {modalRestaurant && (
                            <ScrollView showsVerticalScrollIndicator={false}>
                                {/* Modal Header */}
                                <View style={styles.modalHeader}>
                                    <Text variant="headlineSmall" style={styles.modalTitle}>
                                        {modalRestaurant.name}
                                    </Text>
                                    <IconButton
                                        icon="close"
                                        size={24}
                                        onPress={closeModal}
                                        style={styles.closeButton}
                                    />
                                </View>

                                {/* Chips Row */}
                                <View style={styles.modalChipsRow}>
                                    {modalRestaurant.rating && (
                                        <Chip icon="star" style={styles.modalChip}>
                                            {modalRestaurant.rating}/5
                                        </Chip>
                                    )}
                                    {modalRestaurant.price_level && (
                                        <Chip icon="currency-usd" style={styles.modalChip}>
                                            {modalRestaurant.price_level}
                                        </Chip>
                                    )}
                                    {modalRestaurant.cuisine_type && (
                                        <Chip icon="silverware-fork-knife" style={styles.modalChip}>
                                            {modalRestaurant.cuisine_type}
                                        </Chip>
                                    )}
                                    {modalRestaurant.distance_miles && (
                                        <Chip icon="map-marker-distance" style={styles.modalChip}>
                                            {modalRestaurant.distance_miles.toFixed(1)} mi
                                        </Chip>
                                    )}
                                </View>

                                {/* Description */}
                                {modalRestaurant.description && (
                                    <View style={styles.modalSection}>
                                        <Text variant="bodyMedium" style={styles.modalDescription}>
                                            {modalRestaurant.description}
                                        </Text>
                                    </View>
                                )}

                                {/* Contact Info */}
                                <View style={styles.modalSection}>
                                    <Text variant="titleSmall" style={styles.modalSectionTitle}>
                                        Contact & Location
                                    </Text>

                                    {modalRestaurant.address && (
                                        <TouchableOpacity
                                            style={styles.contactRow}
                                            onPress={() => openDirections(modalRestaurant)}
                                        >
                                            <Text style={styles.contactIcon}>📍</Text>
                                            <Text variant="bodyMedium" style={styles.contactLink}>
                                                {modalRestaurant.address}
                                            </Text>
                                        </TouchableOpacity>
                                    )}

                                    {modalRestaurant.phone && (
                                        <TouchableOpacity
                                            style={styles.contactRow}
                                            onPress={() => openPhone(modalRestaurant.phone)}
                                        >
                                            <Text style={styles.contactIcon}>📞</Text>
                                            <Text variant="bodyMedium" style={styles.contactLink}>
                                                {modalRestaurant.phone}
                                            </Text>
                                        </TouchableOpacity>
                                    )}

                                    {modalRestaurant.website && (
                                        <TouchableOpacity
                                            style={styles.contactRow}
                                            onPress={() => openWebsite(modalRestaurant.website)}
                                        >
                                            <Text style={styles.contactIcon}>🌐</Text>
                                            <Text variant="bodyMedium" style={styles.contactLink} numberOfLines={1}>
                                                {modalRestaurant.website}
                                            </Text>
                                        </TouchableOpacity>
                                    )}
                                </View>

                                {/* Action Buttons */}
                                <View style={styles.actionButtonsRow}>
                                    <TouchableOpacity
                                        style={styles.actionButton}
                                        onPress={() => openDirections(modalRestaurant)}
                                    >
                                        <Text style={styles.actionButtonText}>Get Directions</Text>
                                    </TouchableOpacity>
                                    {modalRestaurant.phone && (
                                        <TouchableOpacity
                                            style={styles.actionButton}
                                            onPress={() => openPhone(modalRestaurant.phone)}
                                        >
                                            <Text style={styles.actionButtonText}>Call</Text>
                                        </TouchableOpacity>
                                    )}
                                    {modalRestaurant.website && (
                                        <TouchableOpacity
                                            style={styles.actionButton}
                                            onPress={() => openWebsite(modalRestaurant.website)}
                                        >
                                            <Text style={styles.actionButtonText}>Website</Text>
                                        </TouchableOpacity>
                                    )}
                                </View>

                                {/* Review Summary Section */}
                                {modalRestaurant.review_summary && (
                                    <View style={styles.modalSection}>
                                        <Text variant="titleSmall" style={styles.modalSectionTitle}>
                                            Customer Reviews
                                        </Text>
                                        <View style={styles.modalReviewSummaryBox}>
                                            <Text variant="bodyMedium" style={styles.modalReviewSummaryText}>
                                                {modalRestaurant.review_summary}
                                            </Text>
                                        </View>
                                    </View>
                                )}
                            </ScrollView>
                        )}
                    </Pressable>
                </Pressable>
            </Modal>
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
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    restaurantName: {
        fontWeight: '600',
        marginBottom: 8,
        flex: 1,
    },
    expandIconButton: {
        margin: -8,
        marginTop: -12,
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
    reviewSummaryContainer: {
        marginTop: 12,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: '#E6E9EF',
    },
    reviewSummaryTitle: {
        fontWeight: '600',
        color: '#262730',
        marginBottom: 8,
    },
    reviewSummaryText: {
        color: '#5F6368',
        lineHeight: 20,
        fontStyle: 'italic',
        flexWrap: 'wrap',
        flexShrink: 1,
    },
    // Modal Styles
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 20,
    },
    modalContent: {
        backgroundColor: '#FFFFFF',
        borderRadius: 16,
        padding: 24,
        maxWidth: 625,
        width: '100%',
        maxHeight: '90%',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.25,
        shadowRadius: 12,
        elevation: 10,
    },
    modalHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 16,
    },
    modalTitle: {
        fontWeight: '700',
        flex: 1,
        paddingRight: 8,
    },
    closeButton: {
        margin: -8,
    },
    modalChipsRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 8,
        marginBottom: 16,
    },
    modalChip: {
        height: 32,
    },
    modalSection: {
        marginBottom: 20,
    },
    modalSectionTitle: {
        fontWeight: '600',
        color: '#262730',
        marginBottom: 12,
    },
    modalDescription: {
        color: '#5F6368',
        lineHeight: 22,
        fontStyle: 'italic',
    },
    contactRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 8,
    },
    contactIcon: {
        fontSize: 16,
        marginRight: 12,
    },
    contactLink: {
        color: '#1A73E8',
        flex: 1,
    },
    actionButtonsRow: {
        flexDirection: 'row',
        gap: 12,
        marginBottom: 20,
    },
    actionButton: {
        flex: 1,
        backgroundColor: '#1A73E8',
        paddingVertical: 12,
        paddingHorizontal: 16,
        borderRadius: 8,
        alignItems: 'center',
    },
    actionButtonText: {
        color: '#FFFFFF',
        fontWeight: '600',
        fontSize: 14,
    },
    modalReviewSummaryBox: {
        backgroundColor: '#F8F9FA',
        borderRadius: 8,
        padding: 16,
        borderLeftWidth: 3,
        borderLeftColor: '#1A73E8',
    },
    modalReviewSummaryText: {
        color: '#5F6368',
        lineHeight: 22,
        fontStyle: 'italic',
        flexWrap: 'wrap',
        flexShrink: 1,
    },
});
