import React, { useState } from 'react';
import LoginPage from '../pages/LoginPage';
import SignupPage from '../pages/SignupPage';
import ForgotPasswordPage from '../pages/ForgotPasswordPage';

const AUTH_SCREENS = {
  LOGIN: 'login',
  SIGNUP: 'signup',
  FORGOT_PASSWORD: 'forgot_password',
};

export default function AuthNavigator({ onLogin }) {
  const [currentScreen, setCurrentScreen] = useState(AUTH_SCREENS.LOGIN);

  const navigateToLogin = () => setCurrentScreen(AUTH_SCREENS.LOGIN);
  const navigateToSignup = () => setCurrentScreen(AUTH_SCREENS.SIGNUP);
  const navigateToForgotPassword = () => setCurrentScreen(AUTH_SCREENS.FORGOT_PASSWORD);

  switch (currentScreen) {
    case AUTH_SCREENS.SIGNUP:
      return (
        <SignupPage
          onSignup={onLogin}
          onNavigateToLogin={navigateToLogin}
        />
      );
    case AUTH_SCREENS.FORGOT_PASSWORD:
      return (
        <ForgotPasswordPage
          onNavigateToLogin={navigateToLogin}
        />
      );
    case AUTH_SCREENS.LOGIN:
    default:
      return (
        <LoginPage
          onLogin={onLogin}
          onNavigateToSignup={navigateToSignup}
          onNavigateToForgotPassword={navigateToForgotPassword}
        />
      );
  }
}

export { AUTH_SCREENS };
