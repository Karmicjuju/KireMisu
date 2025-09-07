"use client"

import React, { useEffect } from 'react'
import { useAuthStore, useTokenRefresh } from '@/lib/auth-store'

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { checkAuth } = useAuthStore()
  
  // Initialize auth check on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])
  
  // Set up automatic token refresh
  useTokenRefresh()
  
  return <>{children}</>
}