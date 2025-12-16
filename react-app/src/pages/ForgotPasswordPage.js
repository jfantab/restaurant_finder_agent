import React, { useState } from 'react';
import { StyleSheet, View, KeyboardAvoidingView, Platform } from 'react-native';
import {
    Text,
    TextInput,
    Button,
    Card,
    HelperText,
} from 'react-native-paper';
import { sendPasswordResetEmail } from 'firebase/auth';
import { auth } from '../firebase';

export default function ForgotPasswordPage({ onNavigateToLogin }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);

    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const getFirebaseErrorMessage = (errorCode) => {
        switch (errorCode) {
            case 'auth/invalid-email':
                return 'Invalid email address';
            case 'auth/user-not-found':
                return 'No account found with this email';
            case 'auth/too-many-requests':
                return 'Too many attempts. Please try again later';
            default:
                return 'Failed to send reset email. Please try again';
        }
    };

    const handleResetPassword = async () => {
        setError('');
        setSuccess(false);

        if (!email.trim()) {
            setError('Please enter your email');
            return;
        }

        if (!validateEmail(email)) {
            setError('Please enter a valid email address');
            return;
        }

        setLoading(true);

        try {
            await sendPasswordResetEmail(auth, email);
            setSuccess(true);
        } catch (err) {
            setError(getFirebaseErrorMessage(err.code));
        } finally {
            setLoading(false);
        }
    };

    return (
        <KeyboardAvoidingView
            style={styles.container}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
            <View style={styles.content}>
                <Card style={styles.card}>
                    <Card.Content>
                        <View style={styles.header}>
                            <Text variant="headlineLarge" style={styles.title}>
                                🔑
                            </Text>
                            <Text variant="headlineMedium" style={styles.appName}>
                                Reset Password
                            </Text>
                            <Text variant="bodyMedium" style={styles.subtitle}>
                                Enter your email to receive a password reset link
                            </Text>
                        </View>

                        <View style={styles.form}>
                            {success ? (
                                <View style={styles.successContainer}>
                                    <Text variant="bodyLarge" style={styles.successText}>
                                        Password reset email sent!
                                    </Text>
                                    <Text variant="bodyMedium" style={styles.successSubtext}>
                                        Check your inbox for a link to reset your password.
                                        If it doesn't appear within a few minutes, check your spam folder.
                                    </Text>
                                </View>
                            ) : (
                                <>
                                    <TextInput
                                        mode="outlined"
                                        label="Email"
                                        value={email}
                                        onChangeText={(text) => {
                                            setEmail(text);
                                            setError('');
                                        }}
                                        keyboardType="email-address"
                                        autoCapitalize="none"
                                        autoComplete="email"
                                        style={styles.input}
                                        disabled={loading}
                                        left={<TextInput.Icon icon="email" />}
                                        onSubmitEditing={handleResetPassword}
                                    />

                                    {error ? (
                                        <HelperText type="error" visible={!!error}>
                                            {error}
                                        </HelperText>
                                    ) : null}

                                    <Button
                                        mode="contained"
                                        onPress={handleResetPassword}
                                        loading={loading}
                                        disabled={loading}
                                        style={styles.button}
                                        contentStyle={styles.buttonContent}
                                    >
                                        {loading ? 'Sending...' : 'Send Reset Link'}
                                    </Button>
                                </>
                            )}

                            <Button
                                mode="text"
                                onPress={onNavigateToLogin}
                                disabled={loading}
                                style={styles.backButton}
                                icon="arrow-left"
                            >
                                Back to Sign In
                            </Button>
                        </View>
                    </Card.Content>
                </Card>
            </View>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#F0F2F6',
    },
    content: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 20,
    },
    card: {
        width: '100%',
        maxWidth: 400,
        backgroundColor: '#FFFFFF',
        borderRadius: 12,
        elevation: 4,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 8,
    },
    header: {
        alignItems: 'center',
        marginBottom: 32,
    },
    title: {
        fontSize: 48,
        marginBottom: 8,
    },
    appName: {
        fontWeight: '600',
        color: '#262730',
        marginBottom: 8,
    },
    subtitle: {
        color: '#5F6368',
        textAlign: 'center',
    },
    form: {
        gap: 16,
    },
    input: {
        backgroundColor: '#FFFFFF',
    },
    button: {
        marginTop: 8,
        borderRadius: 8,
    },
    buttonContent: {
        paddingVertical: 8,
    },
    backButton: {
        marginTop: 8,
    },
    successContainer: {
        backgroundColor: '#E8F5E9',
        padding: 16,
        borderRadius: 8,
        alignItems: 'center',
    },
    successText: {
        color: '#2E7D32',
        fontWeight: '600',
        marginBottom: 8,
        textAlign: 'center',
    },
    successSubtext: {
        color: '#4CAF50',
        textAlign: 'center',
    },
});
