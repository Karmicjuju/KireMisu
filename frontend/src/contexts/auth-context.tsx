'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { configureApiAuth } from '@/lib/api';

export interface User {
  id: string;
  username: string;
  email?: string;
  isAuthenticated: boolean;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  getAuthHeaders: () => Record<string, string>;
  getApiKey: () => string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize authentication state
  useEffect(() => {
    initializeAuth();
  }, []);

  // Configure API client with auth token whenever user state changes
  useEffect(() => {
    configureApiAuth(getApiKey);
  }, [user]);

  const initializeAuth = async () => {
    try {
      // Check if user is already authenticated (e.g., from localStorage, session, etc.)
      const storedAuth = localStorage.getItem('kiremisu_auth');
      if (storedAuth) {
        const authData = JSON.parse(storedAuth);
        
        // Check if token is expired
        if (authData.token && authData.expiresAt > Date.now()) {
          // Verify token with server
          try {
            const response = await fetch('/api/auth/me', {
              headers: {
                'Authorization': `Bearer ${authData.token}`,
              },
            });
            
            if (response.ok) {
              const userData = await response.json();
              setUser({
                id: userData.id,
                username: userData.username,
                email: userData.email,
                isAuthenticated: true,
              });
            } else {
              // Token is invalid, clear it
              localStorage.removeItem('kiremisu_auth');
              localStorage.removeItem('kiremisu_push_subscription');
            }
          } catch (error) {
            console.warn('Failed to verify token with server:', error);
            // Clear auth on verification failure
            localStorage.removeItem('kiremisu_auth');
            localStorage.removeItem('kiremisu_push_subscription');
          }
        } else {
          // Clear expired auth
          localStorage.removeItem('kiremisu_auth');
          localStorage.removeItem('kiremisu_push_subscription');
        }
      }
      // If no stored auth, user starts unauthenticated and needs to log in
    } catch (error) {
      console.error('Failed to initialize auth:', error);
      // Clear potentially corrupted auth data
      localStorage.removeItem('kiremisu_auth');
      localStorage.removeItem('kiremisu_push_subscription');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      // Call authentication API
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username_or_email: username, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed');
      }

      const loginData = await response.json();
      
      const userData = {
        id: loginData.user.id,
        username: loginData.user.username,
        email: loginData.user.email,
        isAuthenticated: true,
      };

      const authData = {
        userId: userData.id,
        username: userData.username,
        email: userData.email,
        token: loginData.access_token,
        expiresAt: Date.now() + (loginData.expires_in * 1000), // Convert to milliseconds
      };

      localStorage.setItem('kiremisu_auth', JSON.stringify(authData));
      setUser(userData);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Call logout API if we have a valid token
      const storedAuth = localStorage.getItem('kiremisu_auth');
      if (storedAuth) {
        try {
          const authData = JSON.parse(storedAuth);
          if (authData.token && authData.expiresAt > Date.now()) {
            await fetch('/api/auth/logout', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${authData.token}`,
                'Content-Type': 'application/json',
              },
            });
          }
        } catch (error) {
          console.warn('Logout API call failed:', error);
          // Continue with local logout even if API fails
        }
      }
      
      // Clear local storage
      localStorage.removeItem('kiremisu_auth');
      localStorage.removeItem('kiremisu_push_subscription');
      
      // Clear user state
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getAuthHeaders = (): Record<string, string> => {
    const storedAuth = localStorage.getItem('kiremisu_auth');
    if (storedAuth) {
      try {
        const authData = JSON.parse(storedAuth);
        if (authData.token && authData.expiresAt > Date.now()) {
          return {
            'Authorization': `Bearer ${authData.token}`,
            'Content-Type': 'application/json',
          };
        }
      } catch (error) {
        console.error('Failed to get auth headers:', error);
      }
    }
    
    // Return default headers if no valid auth
    return {
      'Content-Type': 'application/json',
    };
  };

  const getApiKey = (): string | null => {
    const storedAuth = localStorage.getItem('kiremisu_auth');
    if (storedAuth) {
      try {
        const authData = JSON.parse(storedAuth);
        if (authData.token && authData.expiresAt > Date.now()) {
          return authData.token;
        }
      } catch (error) {
        console.error('Failed to get API key:', error);
      }
    }
    return null;
  };


  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user?.isAuthenticated,
    login,
    logout,
    getAuthHeaders,
    getApiKey,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};