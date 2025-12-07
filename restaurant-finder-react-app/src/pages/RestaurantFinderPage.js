import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, ScrollView, Platform } from 'react-native';
import {
    Text,
    TextInput,
    IconButton,
    ActivityIndicator,
    Chip,
} from 'react-native-paper';
import STButton from '../components/STButton';
import STCard from '../components/STCard';
import ChatMessage from '../components/ChatMessage';
import GoogleMap from '../components/GoogleMap';
import PreferencesSidebar from '../components/PreferencesSidebar';
import config from '../../config';

const API_URL = config.API_URL;

export default function RestaurantFinderPage() {
    // Conversation history management
    const [conversations, setConversations] = useState([
        { messages: [], restaurants: [] },
    ]);
    const [currentConversationIndex, setCurrentConversationIndex] = useState(0);

    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const [userLocation, setUserLocation] = useState(null);
    const [preferences, setPreferences] = useState({
        cuisine: '',
        price_range: '',
        dietary_restrictions: [],
    });
    const [sidebarVisible, setSidebarVisible] = useState(true);
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const scrollViewRef = useRef(null);

    // Get current conversation data
    const currentConversation = conversations[currentConversationIndex];
    const messages = currentConversation.messages;
    const restaurants = currentConversation.restaurants;

    // Get user location on mount
    useEffect(() => {
        if (Platform.OS === 'web' && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    setUserLocation({
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                    });
                },
                (error) => {
                    console.error('Error getting location:', error);
                    // Default to San Francisco
                    setUserLocation({ lat: 37.7749, lng: -122.4194 });
                }
            );
        } else {
            // Default location
            setUserLocation({ lat: 37.7749, lng: -122.4194 });
        }
    }, []);

    const handleSend = async () => {
        if (!inputText.trim() || loading) return;

        const userMessage = { role: 'user', content: inputText };
        const query = inputText;
        setInputText('');
        setLoading(true);

        // Create a new conversation if current one has messages
        if (messages.length > 0) {
            const newConversation = {
                messages: [userMessage],
                restaurants: [],
            };
            setConversations([...conversations, newConversation]);
            setCurrentConversationIndex(conversations.length);
        } else {
            // Update current conversation with user message
            const updatedConversations = [...conversations];
            updatedConversations[currentConversationIndex] = {
                ...updatedConversations[currentConversationIndex],
                messages: [userMessage],
            };
            setConversations(updatedConversations);
        }

        try {
            const response = await fetch(`${API_URL}/api/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    location: userLocation,
                    preferences: preferences,
                }),
            });

            const data = await response.json();

            if (data.success) {
                const assistantMessage = {
                    role: 'assistant',
                    content: data.response,
                    restaurants: data.restaurants,
                };

                // Update the conversation with assistant message and restaurants
                setConversations((prev) => {
                    const updated = [...prev];
                    const targetIndex =
                        messages.length > 0
                            ? prev.length - 1
                            : currentConversationIndex;
                    updated[targetIndex] = {
                        messages: [
                            ...updated[targetIndex].messages,
                            assistantMessage,
                        ],
                        restaurants: data.restaurants || [],
                    };
                    return updated;
                });
            } else {
                const errorMessage = {
                    role: 'assistant',
                    content: `Error: ${data.error}`,
                };

                setConversations((prev) => {
                    const updated = [...prev];
                    const targetIndex =
                        messages.length > 0
                            ? prev.length - 1
                            : currentConversationIndex;
                    updated[targetIndex] = {
                        ...updated[targetIndex],
                        messages: [
                            ...updated[targetIndex].messages,
                            errorMessage,
                        ],
                    };
                    return updated;
                });
            }
        } catch (error) {
            const errorMessage = {
                role: 'assistant',
                content: `Error connecting to server: ${error.message}`,
            };

            setConversations((prev) => {
                const updated = [...prev];
                const targetIndex =
                    messages.length > 0
                        ? prev.length - 1
                        : currentConversationIndex;
                updated[targetIndex] = {
                    ...updated[targetIndex],
                    messages: [...updated[targetIndex].messages, errorMessage],
                };
                return updated;
            });
        } finally {
            setLoading(false);
        }
    };

    const formatPreferences = () => {
        const parts = [];
        if (preferences.cuisine) parts.push(`${preferences.cuisine}`);
        if (preferences.price_range) parts.push(preferences.price_range);
        if (preferences.dietary_restrictions.length > 0) {
            parts.push(preferences.dietary_restrictions.join(', '));
        }
        return parts.length > 0 ? parts.join(' • ') : 'No preferences set';
    };

    const handlePreviousConversation = () => {
        if (currentConversationIndex > 0) {
            setCurrentConversationIndex(currentConversationIndex - 1);
            setSelectedRestaurant(null);
        }
    };

    const handleNextConversation = () => {
        if (currentConversationIndex < conversations.length - 1) {
            setCurrentConversationIndex(currentConversationIndex + 1);
            setSelectedRestaurant(null);
        }
    };

    return (
        <View style={styles.container}>
            {/* Preferences Sidebar */}
            {sidebarVisible && (
                <PreferencesSidebar
                    preferences={preferences}
                    onPreferencesChange={setPreferences}
                    userLocation={userLocation}
                    onLocationChange={setUserLocation}
                    onClose={() => setSidebarVisible(false)}
                />
            )}

            {/* Main Content */}
            <View style={styles.mainContent}>
                {/* Header */}
                <View style={styles.header}>
                    <View style={styles.headerLeft}>
                        {!sidebarVisible && (
                            <IconButton
                                icon="menu"
                                size={24}
                                onPress={() => setSidebarVisible(true)}
                            />
                        )}
                        <Text variant="headlineMedium" style={styles.title}>
                            🍽️ Restaurant Finder AI
                        </Text>
                    </View>
                </View>

                {/* Preferences Bar */}
                <View style={styles.preferencesBar}>
                    <ScrollView
                        horizontal
                        showsHorizontalScrollIndicator={false}
                    >
                        <Text
                            variant="bodyMedium"
                            style={styles.preferencesText}
                        >
                            {formatPreferences()}
                        </Text>
                    </ScrollView>
                </View>

                {/* Two Column Layout */}
                <View style={styles.contentColumns}>
                    {/* Left: Google Maps */}
                    <View style={styles.mapColumn}>
                        <STCard style={styles.mapCard}>
                            <Text
                                variant="titleMedium"
                                style={styles.columnTitle}
                            >
                                Map
                            </Text>
                            <GoogleMap
                                restaurants={restaurants}
                                userLocation={userLocation}
                                onLocationChange={setUserLocation}
                                selectedRestaurant={selectedRestaurant}
                            />
                        </STCard>
                    </View>

                    {/* Right: Chat Interface */}
                    <View style={styles.chatColumn}>
                        <STCard style={styles.chatCard}>
                            <Text
                                variant="titleMedium"
                                style={styles.columnTitle}
                            >
                                Chat
                            </Text>

                            {/* Chat Messages Container */}
                            <View style={styles.chatMessagesContainer}>
                                <ScrollView
                                    ref={scrollViewRef}
                                    style={styles.chatMessages}
                                    contentContainerStyle={styles.chatMessagesContent}
                                    onContentSizeChange={() => {
                                        scrollViewRef.current?.scrollToEnd({
                                            animated: true,
                                        });
                                    }}
                                >
                                    {messages.length === 0 && (
                                        <View style={styles.emptyState}>
                                            <Text
                                                variant="bodyLarge"
                                                style={styles.emptyText}
                                            >
                                                👋 Hello! I'm your AI restaurant
                                                finder assistant.
                                            </Text>
                                            <Text
                                                variant="bodyMedium"
                                                style={styles.emptySubtext}
                                            >
                                                Tell me what kind of food you're
                                                looking for, and I'll help you find
                                                the perfect restaurant!
                                            </Text>
                                        </View>
                                    )}

                                    {messages.map((message, index) => (
                                        <ChatMessage
                                            key={index}
                                            message={message}
                                            selectedRestaurant={selectedRestaurant}
                                            onRestaurantClick={(restaurant) => {
                                                setSelectedRestaurant(restaurant);
                                            }}
                                        />
                                    ))}

                                    {loading && (
                                        <View style={styles.loadingMessage}>
                                            <ActivityIndicator size="small" />
                                            <Text
                                                variant="bodyMedium"
                                                style={styles.loadingText}
                                            >
                                                Searching for restaurants...
                                            </Text>
                                        </View>
                                    )}
                                </ScrollView>
                            </View>

                            {/* Chat Input */}
                            <View style={styles.chatInput}>
                                <TextInput
                                    mode="outlined"
                                    placeholder="What kind of restaurant are you looking for?"
                                    value={inputText}
                                    onChangeText={setInputText}
                                    onSubmitEditing={handleSend}
                                    style={styles.input}
                                    disabled={loading}
                                    right={
                                        <TextInput.Icon
                                            icon="send"
                                            onPress={handleSend}
                                            disabled={
                                                loading || !inputText.trim()
                                            }
                                        />
                                    }
                                />
                            </View>

                            {/* Conversation Navigation */}
                            {conversations.length > 1 && (
                                <View style={styles.conversationNav}>
                                    <IconButton
                                        icon="chevron-left"
                                        size={24}
                                        onPress={handlePreviousConversation}
                                        disabled={
                                            currentConversationIndex === 0
                                        }
                                    />
                                    <Text
                                        variant="bodyMedium"
                                        style={styles.conversationCounter}
                                    >
                                        Conversation{' '}
                                        {currentConversationIndex + 1} of{' '}
                                        {conversations.length}
                                    </Text>
                                    <IconButton
                                        icon="chevron-right"
                                        size={24}
                                        onPress={handleNextConversation}
                                        disabled={
                                            currentConversationIndex ===
                                            conversations.length - 1
                                        }
                                    />
                                </View>
                            )}
                        </STCard>
                    </View>
                </View>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        flexDirection: 'row',
        backgroundColor: '#FFFFFF',
        paddingBottom: 20,
    },
    mainContent: {
        flex: 1,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        paddingBottom: 8,
        borderBottomWidth: 1,
        borderBottomColor: '#E6E9EF',
    },
    headerLeft: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    title: {
        fontWeight: '600',
    },
    preferencesBar: {
        padding: 12,
        paddingHorizontal: 16,
        backgroundColor: '#F0F2F6',
        borderBottomWidth: 1,
        borderBottomColor: '#E6E9EF',
    },
    preferencesText: {
        color: '#5F6368',
    },
    contentColumns: {
        flex: 1,
        flexDirection: 'row',
        padding: 16,
        gap: 16,
        overflow: 'hidden',
    },
    mapColumn: {
        flex: 1,
    },
    chatColumn: {
        flex: 1,
        overflow: 'hidden',
    },
    mapCard: {
        height: '100%',
        padding: 16,
    },
    chatCard: {
        height: '100%',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
    },
    columnTitle: {
        fontWeight: '600',
        marginBottom: 12,
        flexShrink: 0,
    },
    chatMessagesContainer: {
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
    },
    chatMessages: {
        flex: 1,
    },
    chatMessagesContent: {
        flexGrow: 1,
    },
    emptyState: {
        padding: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {
        textAlign: 'center',
        marginBottom: 8,
        fontWeight: '500',
    },
    emptySubtext: {
        textAlign: 'center',
        color: '#5F6368',
    },
    loadingMessage: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        gap: 12,
    },
    loadingText: {
        color: '#5F6368',
    },
    chatInput: {
        flexShrink: 0,
        borderTopWidth: 1,
        borderTopColor: '#E6E9EF',
        paddingTop: 12,
    },
    input: {
        backgroundColor: '#FFFFFF',
    },
    conversationNav: {
        flexShrink: 0,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: 8,
        borderTopWidth: 1,
        borderTopColor: '#E6E9EF',
        marginTop: 8,
    },
    conversationCounter: {
        marginHorizontal: 16,
        color: '#5F6368',
    },
});
