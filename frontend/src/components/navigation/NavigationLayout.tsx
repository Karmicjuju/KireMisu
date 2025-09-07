"use client"

import React, { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { TopHeader } from './TopHeader'
import { useAuthStore } from '@/lib/auth-store'
import { cn } from '@/lib/utils'

interface NavigationLayoutProps {
  children: React.ReactNode
  className?: string
}

export function NavigationLayout({ children, className }: NavigationLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const pathname = usePathname()
  const { isAuthenticated } = useAuthStore()
  
  // Public routes that don't need authentication
  const isPublicRoute = pathname === '/login'

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (mobile) {
        setSidebarCollapsed(true)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // For public routes, show minimal layout
  if (isPublicRoute) {
    return (
      <div className="min-h-screen bg-background">
        {children}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content area */}
      <div className={cn(
        "transition-all duration-300",
        isMobile ? "ml-0" : sidebarCollapsed ? "md:ml-16" : "md:ml-60"
      )}>
        {/* Top header */}
        <TopHeader sidebarCollapsed={sidebarCollapsed} />
        
        {/* Page content */}
        <main className={cn(
          "pt-16 min-h-[calc(100vh-4rem)]",
          className
        )}>
          {children}
        </main>
      </div>
    </div>
  )
}