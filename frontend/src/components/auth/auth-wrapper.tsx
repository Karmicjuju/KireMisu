'use client';

import React from 'react';
import { useAuth } from '../../contexts/auth-context';
import { LoginForm } from './login-form';

interface AuthWrapperProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export const AuthWrapper: React.FC<AuthWrapperProps> = ({ children, requireAuth = true }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gradient-to-br from-background via-muted/30 to-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading KireMisu...</p>
        </div>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) {
    return <LoginForm />;
  }

  // For authenticated users or non-auth-required pages
  return <>{children}</>;
};