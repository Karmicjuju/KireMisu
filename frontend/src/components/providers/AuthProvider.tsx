"use client"

import React, { useEffect } from 'react'
import { useAuthStore, useTokenRefresh } from '@/lib/auth-store'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const checkAuth = useAuthStore(state => state.checkAuth)
  
  // Initialize auth check on mount only once
  useEffect(() => {
    checkAuth()
  }, []) // Remove checkAuth dependency to prevent loops
  
  // Set up automatic token refresh (currently disabled)
  useTokenRefresh()
  
  return <>{children}</>
}