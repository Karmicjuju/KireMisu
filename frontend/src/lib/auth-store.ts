"use client"

import React from 'react'
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { getCurrentUser, logout as apiLogout } from './api'

interface User {
  id: number
  username: string
  email?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  rememberMe: boolean
  lastTokenRefresh: number | null
  
  // Actions
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
  setRememberMe: (remember: boolean) => void
  setLastTokenRefresh: (timestamp: number | null) => void
  login: (user: User, rememberMe?: boolean) => void
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  refreshToken: () => Promise<void>
  reset: () => void
}

const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  rememberMe: false,
  lastTokenRefresh: null,
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      setUser: (user) => {
        set({ 
          user, 
          isAuthenticated: !!user,
          isLoading: false 
        })
      },
      
      setLoading: (loading) => {
        set({ isLoading: loading })
      },
      
      setRememberMe: (remember) => {
        set({ rememberMe: remember })
      },
      
      setLastTokenRefresh: (timestamp) => {
        set({ lastTokenRefresh: timestamp })
      },
      
      login: (user, rememberMe = false) => {
        set({ 
          user, 
          isAuthenticated: true, 
          isLoading: false,
          rememberMe,
          lastTokenRefresh: Date.now()
        })
      },
      
      logout: async () => {
        set({ isLoading: true })
        try {
          // Call API logout to clear httpOnly cookie
          await apiLogout()
          
          // Only reset auth state if logout was successful
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            rememberMe: false,
            lastTokenRefresh: null
          })
        } catch (error) {
          // If logout failed, restore the previous loading state
          set({ isLoading: false })
          console.error('Logout failed:', error)
          throw error // Re-throw to let UI components handle the error
        }
      },
      
      checkAuth: async () => {
        set({ isLoading: true })
        try {
          // Try to get user info using httpOnly cookies
          const user = await getCurrentUser()
          set({ 
            user, 
            isAuthenticated: true, 
            isLoading: false,
            lastTokenRefresh: Date.now()
          })
        } catch (error: any) {
          // Auth failed - mark as unauthenticated but don't redirect if we're already on login
          console.warn('Auth check failed:', error)
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            lastTokenRefresh: null
          })
        }
      },
      
      refreshToken: async () => {
        const { isAuthenticated, lastTokenRefresh } = get()
        
        if (!isAuthenticated) return
        
        // Only refresh if it's been more than 25 minutes since last refresh
        // (backend uses 30-minute token expiry, refresh at 25 minutes for safety)
        const now = Date.now()
        const twentyFiveMinutes = 25 * 60 * 1000
        
        if (lastTokenRefresh && (now - lastTokenRefresh) < twentyFiveMinutes) {
          return
        }
        
        try {
          // Make an authenticated request to refresh the token
          // The backend should automatically refresh the httpOnly cookie
          await getCurrentUser()
          set({ lastTokenRefresh: now })
        } catch (error) {
          console.warn('Token refresh failed:', error)
          // If refresh fails, logout the user
          get().logout()
        }
      },
      
      reset: () => {
        set(initialState)
      }
    }),
    {
      name: 'kiremisu-auth',
      storage: createJSONStorage(() => localStorage),
      // Only persist certain fields
      partialize: (state) => ({ 
        rememberMe: state.rememberMe,
        lastTokenRefresh: state.lastTokenRefresh
      }),
    }
  )
)

// Hook to initialize auth check on app start
export const useAuthInit = () => {
  const checkAuth = useAuthStore(state => state.checkAuth)
  const isLoading = useAuthStore(state => state.isLoading)
  
  // Check auth on mount
  React.useEffect(() => {
    checkAuth()
  }, [checkAuth])
  
  return { isLoading }
}

// Auto token refresh hook - disabled to prevent loops
export const useTokenRefresh = () => {
  // Commenting out auto refresh to prevent continuous loops
  // The backend cookies will handle token refresh automatically
  
  // const refreshToken = useAuthStore(state => state.refreshToken)
  // const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  
  // React.useEffect(() => {
  //   if (!isAuthenticated) return
    
  //   // Set up interval to refresh token every 20 minutes (backend uses 30-minute expiry)
  //   const interval = setInterval(() => {
  //     refreshToken()
  //   }, 20 * 60 * 1000) // 20 minutes
    
  //   return () => clearInterval(interval)
  // }, [refreshToken, isAuthenticated])
}