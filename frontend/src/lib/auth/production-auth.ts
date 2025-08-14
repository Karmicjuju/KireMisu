/**
 * Production authentication using secure HttpOnly cookies
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

export class ProductionAuth {
  private csrfToken: string | null = null;

  private getApiUrl(): string {
    return getApiUrl();
  }

  /**
   * Get CSRF token from meta tag or stored value
   */
  private getCSRFToken(): string | null {
    if (this.csrfToken) {
      return this.csrfToken;
    }

    // Try to get from meta tag (set by server)
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute('content');
    }

    return null;
  }

  /**
   * Set CSRF token
   */
  private setCSRFToken(token: string | null): void {
    this.csrfToken = token;
  }

  /**
   * Get auth headers for API requests
   */
  getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for state-changing requests
    const csrfToken = this.getCSRFToken();
    if (csrfToken && featureFlags.useCSRFProtection) {
      headers['X-CSRF-Token'] = csrfToken;
    }

    return headers;
  }

  /**
   * Login with username and password
   */
  async login(username: string, password: string): Promise<User> {
    const apiUrl = this.getApiUrl();
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
      this.setCSRFToken(loginData.csrf_token);
    }

    const userData: User = {
      id: loginData.user.id,
      username: loginData.user.username,
      email: loginData.user.email,
      isAuthenticated: true,
    };

    return userData;
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      const apiUrl = this.getApiUrl();
      await fetch(`${apiUrl}/api/auth/logout`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        credentials: 'include', // Include cookies
      });
    } catch (error) {
      console.warn('Logout API call failed:', error);
      // Continue with local logout even if API fails
    }

    // Clear CSRF token
    this.setCSRFToken(null);
  }

  /**
   * Check if user is authenticated by verifying session
   */
  async checkAuthentication(): Promise<User | null> {
    try {
      const apiUrl = this.getApiUrl();
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers: this.getAuthHeaders(),
        credentials: 'include', // Include cookies
      });

      if (response.ok) {
        const userData = await response.json();
        return {
          id: userData.id,
          username: userData.username,
          email: userData.email,
          isAuthenticated: true,
        };
      } else {
        // Session is invalid
        return null;
      }
    } catch (error) {
      console.warn('Failed to verify session with server:', error);
      return null;
    }
  }

  /**
   * Get API key - not applicable for cookie auth
   */
  getApiKey(): string | null {
    return null; // Cookie auth doesn't use API keys
  }
}

/**
 * Create production auth provider
 */
export function createProductionAuthProvider(): AuthContextType {
  const auth = new ProductionAuth();

  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  // Initialize authentication state
  React.useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const userData = await auth.checkAuthentication();
      setUser(userData);
    } catch (error) {
      console.error('Failed to initialize auth:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const userData = await auth.login(username, password);
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
      await auth.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getAuthHeaders = (): Record<string, string> => {
    return auth.getAuthHeaders();
  };

  const getApiKey = (): string | null => {
    return auth.getApiKey();
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