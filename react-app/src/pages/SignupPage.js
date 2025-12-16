import React, { useState } from 'react';
import { StyleSheet, View, KeyboardAvoidingView, Platform } from 'react-native';
import {
    Text,
    TextInput,
    Button,
    Card,
    HelperText,
} from 'react-native-paper';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../firebase';

export default function SignupPage({ onSignup, onNavigateToLogin }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    const getFirebaseErrorMessage = (errorCode) => {
        switch (errorCode) {
            case 'auth/invalid-email':
                return 'Invalid email address';
            case 'auth/email-already-in-use':
                return 'An account already exists with this email';
            case 'auth/weak-password':
                return 'Password should be at least 6 characters';
            case 'auth/operation-not-allowed':
                return 'Email/password accounts are not enabled';
            case 'auth/too-many-requests':
                return 'Too many attempts. Please try again later';
            default:
                return 'Failed to create account. Please try again';
        }
    };

    const handleSignUp = async () => {
        setError('');

        if (!email.trim()) {
            setError('Please enter your email');
            return;
        }

        if (!validateEmail(email)) {
            setError('Please enter a valid email address');
            return;
        }

        if (!password) {
            setError('Please enter your password');
            return;
        }

        if (password.length < 6) {
            setError('Password must be at least 6 characters');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        setLoading(true);

        try {
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                email,
                password
            );
            onSignup(userCredential.user);
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
                                🍽️
                            </Text>
                            <Text variant="headlineMedium" style={styles.appName}>
                                Create Account
                            </Text>
                            <Text variant="bodyMedium" style={styles.subtitle}>
                                Sign up to find your perfect meal
                            </Text>
                        </View>

                        <View style={styles.form}>
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
                            />

                            <TextInput
                                mode="outlined"
                                label="Password"
                                value={password}
                                onChangeText={(text) => {
                                    setPassword(text);
                                    setError('');
                                }}
                                secureTextEntry={!showPassword}
                                autoCapitalize="none"
                                autoComplete="new-password"
                                style={styles.input}
                                disabled={loading}
                                left={<TextInput.Icon icon="lock" />}
                                right={
                                    <TextInput.Icon
                                        icon={showPassword ? 'eye-off' : 'eye'}
                                        onPress={() => setShowPassword(!showPassword)}
                                    />
                                }
                            />

                            <TextInput
                                mode="outlined"
                                label="Confirm Password"
                                value={confirmPassword}
                                onChangeText={(text) => {
                                    setConfirmPassword(text);
                                    setError('');
                                }}
                                secureTextEntry={!showConfirmPassword}
                                autoCapitalize="none"
                                autoComplete="new-password"
                                style={styles.input}
                                disabled={loading}
                                left={<TextInput.Icon icon="lock-check" />}
                                right={
                                    <TextInput.Icon
                                        icon={showConfirmPassword ? 'eye-off' : 'eye'}
                                        onPress={() => setShowConfirmPassword(!showConfirmPassword)}
                                    />
                                }
                                onSubmitEditing={handleSignUp}
                            />

                            {error ? (
                                <HelperText type="error" visible={!!error}>
                                    {error}
                                </HelperText>
                            ) : null}

                            <Button
                                mode="contained"
                                onPress={handleSignUp}
                                loading={loading}
                                disabled={loading}
                                style={styles.button}
                                contentStyle={styles.buttonContent}
                            >
                                {loading ? 'Creating account...' : 'Sign Up'}
                            </Button>

                            <Button
                                mode="text"
                                onPress={onNavigateToLogin}
                                disabled={loading}
                                style={styles.switchButton}
                            >
                                Already have an account? Sign In
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
    switchButton: {
        marginTop: 8,
    },
});
