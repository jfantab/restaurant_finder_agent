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
import { transcribeAudio, textToSpeech } from '../services/deepgramService';

const API_URL = config.API_URL;
const STORAGE_KEY = 'restaurant_finder_conversations';

// Helper functions for localStorage
const loadConversationsFromStorage = () => {
    if (Platform.OS === 'web' && typeof localStorage !== 'undefined') {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const parsed = JSON.parse(stored);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    return parsed;
                }
            }
        } catch (e) {
            console.error('Error loading conversations from storage:', e);
        }
    }
    return [{ messages: [], restaurants: [], sessionId: null }];
};

const saveConversationsToStorage = (conversations) => {
    if (Platform.OS === 'web' && typeof localStorage !== 'undefined') {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
        } catch (e) {
            console.error('Error saving conversations to storage:', e);
        }
    }
};

export default function RestaurantFinderPage({ user, onLogout }) {
    // Conversation history management
    // Each conversation has: messages, restaurants, and session_id (for backend continuity)
    // Load from localStorage on initial render
    const [conversations, setConversations] = useState(() => loadConversationsFromStorage());
    const [currentConversationIndex, setCurrentConversationIndex] = useState(0);

    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const [userLocation, setUserLocation] = useState(null);
    const [preferences, setPreferences] = useState({
        cuisine: '',
        price_range: '',
        dietary_restrictions: [],
        distance: 5,
        voiceMode: false,
    });
    const [sidebarVisible, setSidebarVisible] = useState(true);
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const [activeFilters, setActiveFilters] = useState({
        cuisine: null,
        price_level: null,
        rating: null,
        distance: 5,
        dietary: [],
        sort_by: null,
    });
    const scrollViewRef = useRef(null);

    // Voice recording states
    const [isRecording, setIsRecording] = useState(false);
    const [isProcessingVoice, setIsProcessingVoice] = useState(false);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // Voice playback states
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);
    const audioRef = useRef(null);

    // Get current conversation data
    const currentConversation = conversations[currentConversationIndex];
    const messages = currentConversation.messages;

    // Collect ALL restaurants from ALL messages in the conversation (for map display)
    // This ensures map markers show cumulative results (1,2,3... then 6,7,8... etc)
    const allRestaurants = messages.reduce((acc, msg) => {
        if (msg.restaurants && msg.restaurants.length > 0) {
            return [...acc, ...msg.restaurants];
        }
        return acc;
    }, []);

    // Save conversations to localStorage whenever they change
    useEffect(() => {
        saveConversationsToStorage(conversations);
    }, [conversations]);

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

    // Voice recording functions
    const startRecording = async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Voice recording is not supported in this browser.');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunksRef.current = [];

            // Try to use a more compatible audio format
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                ? 'audio/webm;codecs=opus'
                : MediaRecorder.isTypeSupported('audio/webm')
                ? 'audio/webm'
                : '';

            console.log('[Voice] Using MIME type:', mimeType);

            const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                stream.getTracks().forEach(track => track.stop());
                await processVoiceInput(audioBlob);
            };

            mediaRecorder.start();
            setIsRecording(true);
        } catch (error) {
            console.error('Error starting recording:', error);
            alert('Failed to start recording. Please check microphone permissions.');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    const processVoiceInput = async (audioBlob) => {
        setIsProcessingVoice(true);
        try {
            const transcript = await transcribeAudio(audioBlob);
            if (transcript && transcript.trim()) {
                setInputText(transcript);
            }
        } catch (error) {
            console.error('Error processing voice input:', error);
            alert('Failed to transcribe audio. Please try again.');
        } finally {
            setIsProcessingVoice(false);
        }
    };

    const playTextAsVoice = async (text) => {
        if (!text || !preferences.voiceMode) return;

        try {
            setIsPlayingAudio(true);

            // Stop any currently playing audio
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }

            // Generate audio URL from text
            const audioUrl = await textToSpeech(text);

            // Create and play audio element
            const audio = new Audio(audioUrl);
            audioRef.current = audio;

            audio.onended = () => {
                setIsPlayingAudio(false);
                URL.revokeObjectURL(audioUrl);
                audioRef.current = null;
            };

            audio.onerror = (error) => {
                console.error('Error playing audio:', error);
                setIsPlayingAudio(false);
                audioRef.current = null;
            };

            await audio.play();
        } catch (error) {
            console.error('Error converting text to speech:', error);
            setIsPlayingAudio(false);
        }
    };

    const stopAudioPlayback = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
            setIsPlayingAudio(false);
        }
    };

    const handleSend = async () => {
        if (!inputText.trim() || loading) return;

        const userMessage = { role: 'user', content: inputText };
        const query = inputText;
        setInputText('');
        setLoading(true);

        // Add user message to current conversation (don't create new conversation)
        const updatedConversations = [...conversations];
        updatedConversations[currentConversationIndex] = {
            ...updatedConversations[currentConversationIndex],
            messages: [...updatedConversations[currentConversationIndex].messages, userMessage],
        };
        setConversations(updatedConversations);

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
                    session_id: currentConversation.sessionId, // Send session_id for conversation continuity
                    active_filters: activeFilters, // Send current filter state
                }),
            });

            const data = await response.json();

            if (data.success) {
                const assistantMessage = {
                    role: 'assistant',
                    content: data.response,
                    restaurants: data.restaurants,
                };

                // Update the conversation with assistant message, restaurants, and session_id
                setConversations((prev) => {
                    const updated = [...prev];
                    updated[currentConversationIndex] = {
                        messages: [
                            ...updated[currentConversationIndex].messages,
                            assistantMessage,
                        ],
                        restaurants: data.restaurants || updated[currentConversationIndex].restaurants,
                        sessionId: data.session_id, // Store session_id from backend
                    };
                    return updated;
                });

                // Update active filters from backend response
                if (data.filter_state && data.filter_state.filters) {
                    setActiveFilters({
                        cuisine: data.filter_state.filters.cuisine,
                        price_level: data.filter_state.filters.price_level,
                        rating: data.filter_state.filters.rating,
                        distance: data.filter_state.filters.distance,
                        dietary: data.filter_state.filters.dietary || [],
                        sort_by: data.filter_state.filters.sort_by,
                    });
                }

                // Play response as voice if voice mode is enabled
                if (preferences.voiceMode && data.response) {
                    await playTextAsVoice(data.response);
                }
            } else {
                const errorMessage = {
                    role: 'assistant',
                    content: `Error: ${data.error}`,
                };

                setConversations((prev) => {
                    const updated = [...prev];
                    updated[currentConversationIndex] = {
                        ...updated[currentConversationIndex],
                        messages: [
                            ...updated[currentConversationIndex].messages,
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
                updated[currentConversationIndex] = {
                    ...updated[currentConversationIndex],
                    messages: [...updated[currentConversationIndex].messages, errorMessage],
                };
                return updated;
            });
        } finally {
            setLoading(false);
        }
    };

    // Create a new conversation (user-initiated)
    const handleNewConversation = () => {
        const newConversation = { messages: [], restaurants: [], sessionId: null };
        setConversations([...conversations, newConversation]);
        setCurrentConversationIndex(conversations.length);
        setSelectedRestaurant(null);
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

    const handleDeleteConversation = () => {
        if (conversations.length === 1) {
            // If only one conversation, just clear it
            setConversations([{ messages: [], restaurants: [], sessionId: null }]);
            setSelectedRestaurant(null);
        } else {
            // Remove current conversation
            const updated = conversations.filter((_, index) => index !== currentConversationIndex);
            setConversations(updated);
            // Adjust current index if needed
            if (currentConversationIndex >= updated.length) {
                setCurrentConversationIndex(updated.length - 1);
            }
            setSelectedRestaurant(null);
        }
    };

    const handleRemoveFilter = async (filterType, value = null) => {
        const updated = { ...activeFilters };
        if (filterType === 'dietary' && value) {
            updated.dietary = updated.dietary.filter(d => d !== value);
        } else if (filterType === 'distance') {
            updated.distance = 5; // reset to default
        } else {
            updated[filterType] = null;
        }
        setActiveFilters(updated);
        // Re-run search with updated filters
        await handleSend(`Remove ${filterType} filter and show updated results`);
    };

    const handleClearAllFilters = async () => {
        setActiveFilters({
            cuisine: null,
            price_level: null,
            rating: null,
            distance: 5,
            dietary: [],
            sort_by: null,
        });
        // Re-run original search
        await handleSend('Clear all filters and show me all restaurants');
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
                    <View style={styles.headerRight}>
                        {user && (
                            <Text variant="bodyMedium" style={styles.userEmail}>
                                {user.email}
                            </Text>
                        )}
                        <IconButton
                            icon="logout"
                            size={24}
                            onPress={onLogout}
                        />
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

                {/* Active Filters Bar */}
                {(activeFilters.cuisine || activeFilters.price_level || activeFilters.rating ||
                  activeFilters.distance !== 5 || activeFilters.dietary.length > 0 || activeFilters.sort_by) && (
                    <View style={styles.filtersBar}>
                        <ScrollView
                            horizontal
                            showsHorizontalScrollIndicator={false}
                            contentContainerStyle={styles.filtersContent}
                        >
                            <Text variant="bodySmall" style={styles.filtersLabel}>
                                Active filters:
                            </Text>
                            {activeFilters.cuisine && (
                                <Chip
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('cuisine')}
                                    style={styles.filterChip}
                                >
                                    {activeFilters.cuisine}
                                </Chip>
                            )}
                            {activeFilters.price_level && (
                                <Chip
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('price_level')}
                                    style={styles.filterChip}
                                >
                                    {'$'.repeat(activeFilters.price_level)}
                                </Chip>
                            )}
                            {activeFilters.rating && (
                                <Chip
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('rating')}
                                    style={styles.filterChip}
                                >
                                    ≥{activeFilters.rating}★
                                </Chip>
                            )}
                            {activeFilters.distance !== 5 && (
                                <Chip
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('distance')}
                                    style={styles.filterChip}
                                >
                                    within {activeFilters.distance}mi
                                </Chip>
                            )}
                            {activeFilters.dietary.map((dietary) => (
                                <Chip
                                    key={dietary}
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('dietary', dietary)}
                                    style={styles.filterChip}
                                >
                                    {dietary}
                                </Chip>
                            ))}
                            {activeFilters.sort_by && (
                                <Chip
                                    mode="outlined"
                                    onClose={() => handleRemoveFilter('sort_by')}
                                    style={styles.filterChip}
                                >
                                    Sort: {activeFilters.sort_by}
                                </Chip>
                            )}
                            <IconButton
                                icon="close-circle"
                                size={20}
                                onPress={handleClearAllFilters}
                            />
                        </ScrollView>
                    </View>
                )}

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
                                restaurants={allRestaurants}
                                userLocation={userLocation}
                                onLocationChange={setUserLocation}
                                selectedRestaurant={selectedRestaurant}
                            />
                        </STCard>
                    </View>

                    {/* Right: Chat Interface */}
                    <View style={styles.chatColumn}>
                        <STCard style={styles.chatCard}>
                            {/* Chat Header with New Chat and Delete buttons */}
                            <View style={styles.chatHeader}>
                                <Text
                                    variant="titleMedium"
                                    style={styles.columnTitle}
                                >
                                    Chat
                                </Text>
                                <View style={styles.chatHeaderButtons}>
                                    <IconButton
                                        icon="delete-outline"
                                        size={24}
                                        onPress={handleDeleteConversation}
                                        disabled={loading}
                                    />
                                    <IconButton
                                        icon="plus-circle"
                                        size={24}
                                        onPress={handleNewConversation}
                                    />
                                </View>
                            </View>

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

                                    {messages.map((message, index) => {
                                        // Calculate starting index based on restaurants in previous messages
                                        const startingIndex = messages
                                            .slice(0, index)
                                            .reduce((count, msg) => count + (msg.restaurants?.length || 0), 0);
                                        return (
                                            <ChatMessage
                                                key={index}
                                                message={message}
                                                selectedRestaurant={selectedRestaurant}
                                                onRestaurantClick={(restaurant) => {
                                                    setSelectedRestaurant(restaurant);
                                                }}
                                                startingIndex={startingIndex}
                                            />
                                        );
                                    })}

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

                            {/* Voice Playback Indicator */}
                            {isPlayingAudio && (
                                <View style={styles.voicePlaybackIndicator}>
                                    <ActivityIndicator size="small" color="#007AFF" />
                                    <Text variant="bodyMedium" style={styles.voicePlaybackText}>
                                        Speaking response...
                                    </Text>
                                    <IconButton
                                        icon="stop"
                                        size={20}
                                        onPress={stopAudioPlayback}
                                        iconColor="#FF3B30"
                                    />
                                </View>
                            )}

                            {/* Chat Input */}
                            <View style={styles.chatInput}>
                                <View style={styles.inputRow}>
                                    {Platform.OS === 'web' && (
                                        <IconButton
                                            icon={isRecording ? 'stop' : 'microphone'}
                                            size={24}
                                            onPress={isRecording ? stopRecording : startRecording}
                                            disabled={loading || isProcessingVoice}
                                            iconColor={isRecording ? '#FF3B30' : '#007AFF'}
                                            style={styles.micButton}
                                        />
                                    )}
                                    <TextInput
                                        mode="outlined"
                                        placeholder={isProcessingVoice ? 'Processing voice...' : 'What kind of restaurant are you looking for?'}
                                        value={inputText}
                                        onChangeText={setInputText}
                                        onSubmitEditing={handleSend}
                                        style={styles.input}
                                        disabled={loading || isProcessingVoice}
                                        right={
                                            <TextInput.Icon
                                                icon="send"
                                                onPress={handleSend}
                                                disabled={
                                                    loading || !inputText.trim() || isProcessingVoice
                                                }
                                            />
                                        }
                                    />
                                </View>
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
    headerRight: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    userEmail: {
        color: '#5F6368',
        marginRight: 4,
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
    filtersBar: {
        padding: 8,
        paddingHorizontal: 16,
        backgroundColor: '#E8F4F8',
        borderBottomWidth: 1,
        borderBottomColor: '#B3E5FC',
    },
    filtersContent: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    filtersLabel: {
        color: '#01579B',
        fontWeight: '500',
        marginRight: 4,
    },
    filterChip: {
        backgroundColor: '#FFFFFF',
        borderColor: '#4FC3F7',
    },
    contentColumns: {
        flex: 1,
        flexDirection: 'row',
        padding: 16,
        gap: 16,
        overflow: 'hidden',
        minHeight: 0,
    },
    mapColumn: {
        flex: 1,
    },
    chatColumn: {
        flex: 1,
        minHeight: 0,
        overflow: 'hidden',
    },
    mapCard: {
        height: '100%',
        padding: 16,
    },
    chatCard: {
        flex: 1,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        minHeight: 0,
    },
    columnTitle: {
        fontWeight: '600',
        marginBottom: 0,
        flexShrink: 0,
    },
    chatHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
        flexShrink: 0,
    },
    chatHeaderButtons: {
        flexDirection: 'row',
        alignItems: 'center',
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
        paddingBottom: 16,
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
    voicePlaybackIndicator: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        paddingHorizontal: 16,
        backgroundColor: '#E3F2FD',
        borderTopWidth: 1,
        borderTopColor: '#90CAF9',
        gap: 12,
    },
    voicePlaybackText: {
        flex: 1,
        color: '#1976D2',
        fontWeight: '500',
    },
    chatInput: {
        flexShrink: 0,
        borderTopWidth: 1,
        borderTopColor: '#E6E9EF',
        paddingTop: 12,
    },
    inputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    micButton: {
        margin: 0,
    },
    input: {
        backgroundColor: '#FFFFFF',
        flex: 1,
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
