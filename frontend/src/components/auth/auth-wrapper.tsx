'use client';

import React from 'react';
import { useAuth } from '../../contexts/auth-context';
import { LoginForm } from './login-form';

interface AuthWrapperProps {
  children: React.ReactNode;
  requireAuth?: boolean;
}

export const AuthWrapper: React.FC<AuthWrapperProps> = ({ children, requireAuth = true }) => {
  const { isAuthenticated, isLoading, user, logout } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{
          width: '2rem',
          height: '2rem',
          border: '2px solid #e5e7eb',
          borderTop: '2px solid #4f46e5',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p style={{ color: '#6b7280' }}>Loading...</p>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: '#f9fafb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem'
      }}>
        <LoginForm />
      </div>
    );
  }

  if (isAuthenticated && user) {
    return (
      <>
        {/* User info bar - only show if authenticated */}
        <div style={{
          backgroundColor: '#f3f4f6',
          padding: '0.5rem 1rem',
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.875rem',
          color: '#6b7280'
        }}>
          <span>
            Welcome back, <strong>{user.username}</strong>
            {user.email && (
              <span style={{ marginLeft: '0.5rem', opacity: 0.8 }}>
                ({user.email})
              </span>
            )}
          </span>
          <button
            onClick={logout}
            style={{
              color: '#dc2626',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.875rem',
              textDecoration: 'underline'
            }}
          >
            Sign out
          </button>
        </div>
        {children}
      </>
    );
  }

  // For non-auth-required pages when not authenticated
  return <>{children}</>;
};