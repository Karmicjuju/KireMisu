'use client';

import React, { useState } from 'react';
import { useAuth } from '../../contexts/auth-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface LoginFormProps {
  onSuccess?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showDemoUsers, setShowDemoUsers] = useState(false);
  const { login, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError('Please enter both username and password');
      return;
    }

    try {
      await login(username, password);
      onSuccess?.();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed');
    }
  };

  const handleDemoLogin = async (demoUsername: string, demoPassword: string) => {
    setUsername(demoUsername);
    setPassword(demoPassword);
    setError('');

    try {
      await login(demoUsername, demoPassword);
      onSuccess?.();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Login failed');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-muted/30 to-background p-6">
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <div className="h-8 w-8 rounded-full bg-primary shadow-lg shadow-primary/25" />
          </div>
          <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
            Welcome to KireMisu
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Sign in to access your manga library
          </p>
        </div>

        {/* Login Form */}
        <div className="rounded-lg border bg-card p-8 shadow-lg shadow-black/5">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label 
                htmlFor="username" 
                className="text-sm font-medium text-card-foreground"
              >
                Username
              </label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                disabled={isLoading}
                className="transition-all focus:ring-primary/20"
              />
            </div>

            <div className="space-y-2">
              <label 
                htmlFor="password" 
                className="text-sm font-medium text-card-foreground"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                disabled={isLoading}
                className="transition-all focus:ring-primary/20"
              />
            </div>

            {error && (
              <div className="rounded-md bg-destructive/15 border border-destructive/20 p-3">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}

            <Button 
              type="submit" 
              className="w-full h-11 bg-primary hover:bg-primary/90 text-primary-foreground font-medium transition-all shadow-md hover:shadow-lg disabled:opacity-50"
              disabled={isLoading}
            >
              {isLoading ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Signing in...
                </div>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          {/* Demo Users Section */}
          <div className="mt-6 pt-6 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowDemoUsers(!showDemoUsers)}
              className="w-full text-muted-foreground hover:text-foreground"
            >
              {showDemoUsers ? '↑ Hide' : '↓ Show'} demo accounts
            </Button>

            {showDemoUsers && (
              <div className="mt-4 space-y-2">
                <p className="text-xs text-muted-foreground text-center mb-3">
                  Demo accounts for development and testing
                </p>
                
                <div className="grid gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDemoLogin('demo', 'demo123')}
                    disabled={isLoading}
                    className="justify-start text-left h-auto p-3"
                  >
                    <div>
                      <div className="font-medium">demo / demo123</div>
                      <div className="text-xs text-muted-foreground">Regular user account</div>
                    </div>
                  </Button>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDemoLogin('admin', 'admin123')}
                    disabled={isLoading}
                    className="justify-start text-left h-auto p-3"
                  >
                    <div>
                      <div className="font-medium">admin / admin123</div>
                      <div className="text-xs text-muted-foreground">Administrator account</div>
                    </div>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          Self-hosted manga reader and library management system
        </p>
      </div>
    </div>
  );
};