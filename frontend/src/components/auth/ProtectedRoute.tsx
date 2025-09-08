"use client"

import React from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/auth-store'
import { Card, CardContent } from '@/components/ui/card'

interface ProtectedRouteProps {
  children: React.ReactNode
  fallback?: React.ReactNode
}

export function ProtectedRoute({ 
  children, 
  fallback
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthStore()
  const router = useRouter()
  const hasRedirected = React.useRef(false)
  
  // Handle redirect to login page for unauthenticated users
  React.useEffect(() => {
    // Only redirect if loading is complete, user is not authenticated, and we haven't already redirected
    if (!isLoading && !isAuthenticated && !hasRedirected.current) {
      hasRedirected.current = true
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])
  
  // Reset redirect flag when authentication state changes
  React.useEffect(() => {
    if (isAuthenticated) {
      hasRedirected.current = false
    }
  }, [isAuthenticated])
  
  // Show loading state while AuthProvider initializes
  if (isLoading) {
    return fallback || <ProtectedRouteLoading />
  }
  
  // If not authenticated, show loading state while redirect happens
  if (!isAuthenticated) {
    return fallback || <ProtectedRouteLoading />
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

function NotAuthenticatedMessage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center space-y-4">
            <p className="text-sm text-muted-foreground">
              Please log in to access this page.
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
  }
) {
  const WrappedComponent = (props: P) => (
    <ProtectedRoute 
      fallback={options?.fallback}
    >
      <Component {...props} />
    </ProtectedRoute>
  )
  
  WrappedComponent.displayName = `withProtectedRoute(${Component.displayName || Component.name})`
  
  return WrappedComponent
}