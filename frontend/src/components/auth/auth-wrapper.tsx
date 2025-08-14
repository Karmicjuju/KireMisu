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
  const [hasMounted, setHasMounted] = React.useState(false);

  // Prevent hydration mismatch by waiting for client-side mount
  React.useEffect(() => {
    setHasMounted(true);
  }, []);

  // Show loading state until both mounted and auth is resolved
  if (!hasMounted || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-muted/30 to-background">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
            <h2 className="mt-6 text-3xl font-bold tracking-tight text-foreground">
              KireMisu
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Loading your manga library...
            </p>
          </div>
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