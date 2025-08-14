'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { configureApiAuth } from '@/lib/api';
import { featureFlags } from '@/lib/feature-flags';

interface LoginResponse {
  access_token?: string | null;
  token_type: string;
  expires_in: number;
  user: any;
  auth_method: string;
  csrf_token?: string;
}

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
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [csrfToken, setCsrfToken] = React.useState<string | null>(null);

  console.log('AUTH PROVIDER MOUNTED');
  console.log('Feature flags:', {
    useTestAuth: featureFlags.useTestAuth,
    useSecureAuth: featureFlags.useSecureAuth,
    environment: featureFlags.environment,
    authMethod: featureFlags.authMethod
  });

  const getApiUrl = (): string => {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  };

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for cookie-based auth
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  };

  const checkAuthentication = async (): Promise<User | null> => {
    try {
      const apiUrl = getApiUrl();
      const headers = getAuthHeaders();
      
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers,
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
        // Not authenticated
        setUser(null);
        return null;
      }
    } catch (error) {
      console.warn('Failed to verify session with server:', error);
      setUser(null);
      return null;
    }
  };

  // Initialize authentication on mount
  React.useEffect(() => {
    let mounted = true;
    
    const initializeAuth = async () => {
      try {
        console.log('Auth: Starting initialization');
        
        // Check for stored CSRF token from previous login
        const storedAuth = localStorage.getItem('kiremisu_auth');
        
        if (storedAuth) {
          try {
            const authData = JSON.parse(storedAuth);
            console.log('Auth: Found stored auth data');
            
            if (authData.authMethod === 'secure_cookies' && authData.csrfToken) {
              setCsrfToken(authData.csrfToken);
              console.log('Auth: Set CSRF token');
            }
          } catch (parseError) {
            console.warn('Auth: Failed to parse stored auth data:', parseError);
            localStorage.removeItem('kiremisu_auth');
          }
        }

        // Check authentication with server
        console.log('Auth: Checking with server');
        const result = await checkAuthentication();
        console.log('Auth: Server check result:', result ? 'authenticated' : 'not authenticated');
      } catch (error) {
        console.error('Auth: Failed to initialize:', error);
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          console.log('Auth: Setting loading to false');
          setIsLoading(false);
        }
      }
    };

    initializeAuth();
    
    return () => {
      mounted = false;
    };
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

      const loginData = await response.json();

      // Store CSRF token if provided
      if (loginData.csrf_token) {
        setCsrfToken(loginData.csrf_token);
        
        // Store auth data for future sessions
        localStorage.setItem('kiremisu_auth', JSON.stringify({
          authMethod: 'secure_cookies',
          csrfToken: loginData.csrf_token,
          user: loginData.user
        }));
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

    // Clear state and stored data
    setCsrfToken(null);
    setUser(null);
    localStorage.removeItem('kiremisu_auth');
    localStorage.removeItem('kiremisu_push_subscription');
  };

  const getApiKey = (): string | null => {
    return null; // Cookie auth doesn't use API keys
  };

  const authContextValue: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user?.isAuthenticated,
    login,
    logout,
    getAuthHeaders,
    getApiKey,
  };

  // Configure API client with auth headers whenever user state changes
  React.useEffect(() => {
    configureApiAuth(getAuthHeaders);
  }, [user, csrfToken]);

  return (
    <AuthContext.Provider value={authContextValue}>
      {children}
    </AuthContext.Provider>
  );
};