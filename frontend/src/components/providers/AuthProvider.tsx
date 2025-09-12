"use client"

import React, { useEffect, useRef } from 'react'
import { useAuthStore, useTokenRefresh } from '@/lib/auth-store'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const checkAuth = useAuthStore(state => state.checkAuth)
  const setLoading = useAuthStore(state => state.setLoading)
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const user = useAuthStore(state => state.user)
  const hasInitialized = useRef(false)
  
  // Initialize auth check on mount - only call once per app session
  useEffect(() => {
    // Prevent multiple initialization calls
    if (hasInitialized.current) {
      return
    }
    
    hasInitialized.current = true
    
    // If we already have persisted authentication state, trust it and skip server check
    if (isAuthenticated && user) {
      setLoading(false)
      return
    }
    
    // Only call checkAuth if we don't have persisted auth state
    // Set a timeout for the auth check to prevent indefinite loading
    const authTimeout = setTimeout(() => {
      // If auth check hasn't completed in 5 seconds, assume user is not authenticated
      setLoading(false)
    }, 5000)
    
    checkAuth().finally(() => {
      clearTimeout(authTimeout)
    })
  }, [checkAuth, setLoading, isAuthenticated, user]) // Include dependencies to avoid stale closures
  
  // Set up automatic token refresh (currently disabled to prevent loops)
  useTokenRefresh()
  
  return <>{children}</>
}