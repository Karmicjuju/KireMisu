/**
 * Simplified production authentication using secure HttpOnly cookies
 * This version uses React hooks for proper state management
 */

import React from 'react';
import { User, AuthContextType } from '@/contexts/auth-context';
import { featureFlags, getApiUrl } from '@/lib/feature-flags';

export interface LoginResponse {
  access_token?: string;
  token_type: string;
  expires_in: number;
  user: any;
  auth_method: string;
  csrf_token?: string;
}


/**
 * Create production auth provider using React hooks
 */
export function createProductionAuthProvider(): AuthContextType {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [csrfToken, setCsrfToken] = React.useState<string | null>(null);

  const getApiUrl = (): string => {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  };

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for state-changing requests
    if (csrfToken && featureFlags.useCSRFProtection) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  };

  const checkAuthentication = async (): Promise<User | null> => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers: getAuthHeaders(),
        credentials: 'include', // Include cookies
      });

      if (response.ok) {
        const userData = await response.json();
        const authUser: User = {
          id: userData.id,
          username: userData.username,
          email: userData.email,
          isAuthenticated: true,
        };
        setUser(authUser);
        return authUser;
      } else {
        // Session is invalid
        setUser(null);
        return null;
      }
    } catch (error) {
      console.warn('Failed to verify session with server:', error);
      setUser(null);
      return null;
    }
  };

  // Initialize auth on mount
  React.useEffect(() => {
    const initializeAuth = async () => {
      try {
        await checkAuthentication();
      } catch (error) {
        console.error('Failed to initialize auth:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (username: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const apiUrl = getApiUrl();
      const requestPayload = { username_or_email: username, password };

      const response = await fetch(`${apiUrl}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
        credentials: 'include', // Include cookies
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific HTTP status codes
        if (response.status === 429) {
          throw new Error(errorData.message || errorData.detail || 'Too many login attempts. Please try again later.');
        } else if (response.status === 401) {
          throw new Error(errorData.detail || 'Invalid username or password.');
        } else if (response.status >= 500) {
          throw new Error('Authentication service temporarily unavailable. Please try again later.');
        }
        
        throw new Error(errorData.detail || errorData.message || 'Login failed');
      }

      const loginData: LoginResponse = await response.json();

      // Store CSRF token if provided
      if (loginData.csrf_token) {
        setCsrfToken(loginData.csrf_token);
      }

      const userData: User = {
        id: loginData.user.id,
        username: loginData.user.username,
        email: loginData.user.email,
        isAuthenticated: true,
      };

      setUser(userData);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      const apiUrl = getApiUrl();
      await fetch(`${apiUrl}/api/auth/logout`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include', // Include cookies
      });
    } catch (error) {
      console.warn('Logout API call failed:', error);
      // Continue with local logout even if API fails
    }

    // Clear CSRF token and user
    setCsrfToken(null);
    setUser(null);
  };

  const getApiKey = (): string | null => {
    return null; // Cookie auth doesn't use API keys
  };

  return {
    user,
    isLoading,
    isAuthenticated: !!user?.isAuthenticated,
    login,
    logout,
    getAuthHeaders,
    getApiKey,
  };
}