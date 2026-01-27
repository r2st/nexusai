/**
 * Authentication Context
 * 
 * Manages user authentication state across the app.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { api } from '../services/api';

interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  hasCompletedOnboarding: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signOut: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [hasCompletedOnboarding, setHasCompletedOnboarding] = useState(false);

  useEffect(() => {
    loadStoredAuth();
  }, []);

  async function loadStoredAuth() {
    try {
      const token = await SecureStore.getItemAsync('authToken');
      const onboarded = await SecureStore.getItemAsync('hasCompletedOnboarding');
      
      if (token) {
        api.setAuthToken(token);
        const userData = await api.getCurrentUser();
        setUser(userData);
      }
      
      setHasCompletedOnboarding(onboarded === 'true');
    } catch (error) {
      console.error('Failed to load auth:', error);
    } finally {
      setIsLoading(false);
    }
  }

  async function signIn(email: string, password: string) {
    const response = await api.signIn(email, password);
    await SecureStore.setItemAsync('authToken', response.token);
    api.setAuthToken(response.token);
    setUser(response.user);
  }

  async function signUp(email: string, password: string, name: string) {
    const response = await api.signUp(email, password, name);
    await SecureStore.setItemAsync('authToken', response.token);
    api.setAuthToken(response.token);
    setUser(response.user);
  }

  async function signOut() {
    await SecureStore.deleteItemAsync('authToken');
    api.setAuthToken(null);
    setUser(null);
  }

  async function completeOnboarding() {
    await SecureStore.setItemAsync('hasCompletedOnboarding', 'true');
    setHasCompletedOnboarding(true);
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!user,
        isLoading,
        user,
        hasCompletedOnboarding,
        signIn,
        signUp,
        signOut,
        completeOnboarding,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
