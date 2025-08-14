/**
 * Test authentication with simplified bypass for E2E testing
 */

import React from 'react';
import { User, AuthContextType } from '@/contexts/auth-context';
import { featureFlags, getApiUrl } from '@/lib/feature-flags';

export class TestAuth {
  private testUser: User | null = null;

  private getApiUrl(): string {
    return getApiUrl();
  }

  /**
   * Get auth headers for API requests
   */
  getAuthHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'X-Test-Mode': 'true',
    };
  }

  /**
   * Simplified test login
   */
  async login(username: string, password: string): Promise<User> {
    const apiUrl = this.getApiUrl();
    const requestPayload = { username_or_email: username, password };

    const response = await fetch(`${apiUrl}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Test-Mode': 'true',
      },
      body: JSON.stringify(requestPayload),
      credentials: 'include', // Include test cookies
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || errorData.message || 'Test login failed');
    }

    const loginData = await response.json();
    
    const userData: User = {
      id: loginData.user.id,
      username: loginData.user.username,
      email: loginData.user.email,
      isAuthenticated: true,
    };

    this.testUser = userData;
    return userData;
  }

  /**
   * Test logout
   */
  async logout(): Promise<void> {
    try {
      const apiUrl = this.getApiUrl();
      await fetch(`${apiUrl}/api/auth/logout`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        credentials: 'include',
      });
    } catch (error) {
      console.warn('Test logout API call failed:', error);
    }

    this.testUser = null;
  }

  /**
   * Check test authentication
   */
  async checkAuthentication(): Promise<User | null> {
    if (this.testUser) {
      return this.testUser;
    }

    try {
      const apiUrl = this.getApiUrl();
      const response = await fetch(`${apiUrl}/api/auth/me`, {
        headers: this.getAuthHeaders(),
        credentials: 'include',
      });

      if (response.ok) {
        const userData = await response.json();
        const user: User = {
          id: userData.id,
          username: userData.username,
          email: userData.email,
          isAuthenticated: true,
        };
        this.testUser = user;
        return user;
      }
    } catch (error) {
      console.warn('Test auth check failed:', error);
    }

    return null;
  }

  /**
   * Get API key - not used in test mode
   */
  getApiKey(): string | null {
    return null;
  }

  /**
   * Create test user directly (bypassing normal auth)
   */
  createTestUser(userData: Partial<User>): User {
    const user: User = {
      id: userData.id || 'test-user-1',
      username: userData.username || 'testuser',
      email: userData.email || 'test@example.com',
      isAuthenticated: true,
    };

    this.testUser = user;
    return user;
  }

  /**
   * Clear test user
   */
  clearTestUser(): void {
    this.testUser = null;
  }
}

/**
 * Create test auth provider for E2E testing
 */
export function createTestAuthProvider(): AuthContextType {
  const auth = new TestAuth();

  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  // Initialize test authentication
  React.useEffect(() => {
    initializeTestAuth();
  }, []);

  const initializeTestAuth = async () => {
    try {
      // In test mode, we might have a pre-existing session
      const userData = await auth.checkAuthentication();
      setUser(userData);
    } catch (error) {
      console.error('Failed to initialize test auth:', error);
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
      console.error('Test login failed:', error);
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
      console.error('Test logout failed:', error);
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

  // Expose test-specific methods for E2E testing
  const testHelpers = {
    createTestUser: (userData: Partial<User>) => {
      const user = auth.createTestUser(userData);
      setUser(user);
      return user;
    },
    clearTestUser: () => {
      auth.clearTestUser();
      setUser(null);
    },
  };

  // Add test helpers to global scope for E2E tests
  if (typeof window !== 'undefined' && featureFlags.isTest) {
    (window as any).__testAuth = testHelpers;
  }

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