"use client"

import React, { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/lib/auth-store'
import { Card, CardContent } from '@/components/ui/card'

interface ProtectedRouteProps {
  children: React.ReactNode
  fallback?: React.ReactNode
  redirectTo?: string
}

export function ProtectedRoute({ 
  children, 
  fallback,
  redirectTo = '/login' 
}: ProtectedRouteProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore()
  
  useEffect(() => {
    // Check authentication status
    checkAuth()
  }, [checkAuth])
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      // Allowlist of safe redirect paths to prevent open redirect vulnerability
      const ALLOWED_REDIRECTS = [
        '/',
        '/dashboard', 
        '/library',
        '/profile', 
        '/settings',
        '/series',
        '/chapter',
        '/reader'
      ]
      
      // Validate redirect path against allowlist
      const isAllowedRedirect = (path: string) => {
        return ALLOWED_REDIRECTS.some(allowed => path.startsWith(allowed)) || path === '/'
      }
      
      // Only add redirect parameter if current path is in allowlist
      let redirectUrl = redirectTo
      if (isAllowedRedirect(pathname)) {
        redirectUrl = `${redirectTo}?redirect=${encodeURIComponent(pathname)}`
      }
      
      router.push(redirectUrl)
    }
  }, [isAuthenticated, isLoading, router, pathname, redirectTo])
  
  // Show loading state
  if (isLoading) {
    return fallback || <ProtectedRouteLoading />
  }
  
  // Show nothing while redirecting
  if (!isAuthenticated) {
    return null
  }
  
  // Show protected content
  return <>{children}</>
}

function ProtectedRouteLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center space-y-4">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
            <p className="text-sm text-muted-foreground">
              Checking authentication...
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Higher-order component version for easier usage
export function withProtectedRoute<P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    fallback?: React.ReactNode
    redirectTo?: string
  }
) {
  const WrappedComponent = (props: P) => (
    <ProtectedRoute 
      fallback={options?.fallback} 
      redirectTo={options?.redirectTo}
    >
      <Component {...props} />
    </ProtectedRoute>
  )
  
  WrappedComponent.displayName = `withProtectedRoute(${Component.displayName || Component.name})`
  
  return WrappedComponent
}