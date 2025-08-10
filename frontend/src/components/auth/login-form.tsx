'use client';

import React, { useState } from 'react';
import { useAuth } from '../../contexts/auth-context';

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
    <div style={{
      maxWidth: '400px',
      margin: '0 auto',
      padding: '2rem',
      border: '1px solid #e5e7eb',
      borderRadius: '0.5rem',
      backgroundColor: 'white',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937' }}>
          Sign in to KireMisu
        </h2>
        <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>
          Enter your credentials to access your manga library
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <label 
            htmlFor="username" 
            style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: '500', 
              color: '#374151',
              marginBottom: '0.5rem'
            }}
          >
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              backgroundColor: isLoading ? '#f9fafb' : 'white',
              color: '#1f2937'
            }}
            placeholder="Enter your username"
          />
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label 
            htmlFor="password" 
            style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: '500', 
              color: '#374151',
              marginBottom: '0.5rem'
            }}
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              backgroundColor: isLoading ? '#f9fafb' : 'white',
              color: '#1f2937'
            }}
            placeholder="Enter your password"
          />
        </div>

        {error && (
          <div style={{
            padding: '0.75rem',
            marginBottom: '1rem',
            backgroundColor: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: '0.375rem',
            color: '#dc2626',
            fontSize: '0.875rem'
          }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          style={{
            width: '100%',
            padding: '0.75rem',
            backgroundColor: isLoading ? '#9ca3af' : '#4f46e5',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: '500',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
        >
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
        <button
          type="button"
          onClick={() => setShowDemoUsers(!showDemoUsers)}
          style={{
            color: '#4f46e5',
            fontSize: '0.875rem',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textDecoration: 'underline'
          }}
        >
          {showDemoUsers ? 'Hide' : 'Show'} demo accounts
        </button>
      </div>

      {showDemoUsers && (
        <div style={{
          marginTop: '1rem',
          padding: '1rem',
          backgroundColor: '#f3f4f6',
          borderRadius: '0.375rem'
        }}>
          <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
            Demo accounts for development:
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              onClick={() => handleDemoLogin('demo', 'demo123')}
              disabled={isLoading}
              style={{
                padding: '0.5rem',
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.25rem',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                textAlign: 'left'
              }}
            >
              <strong>demo</strong> / demo123 - Regular user account
            </button>
            
            <button
              onClick={() => handleDemoLogin('admin', 'admin123')}
              disabled={isLoading}
              style={{
                padding: '0.5rem',
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '0.25rem',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontSize: '0.75rem',
                textAlign: 'left'
              }}
            >
              <strong>admin</strong> / admin123 - Admin account
            </button>
          </div>
        </div>
      )}
    </div>
  );
};